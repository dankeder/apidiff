from aiohttp import ClientSession
import argparse
import asyncio
import difflib
import json
import os
import sys
import traceback


class ApiDiffException(Exception):
    pass


async def parseargs():
    parser = argparse.ArgumentParser(
        description='Diff tool for web APIs',
        add_help=True)
    parser.add_argument('url_a',
        type=str,
        metavar='url_a',
        help='URL A')
    parser.add_argument('url_b',
        type=str,
        metavar='url_b',
        help='URL B')
    parser.add_argument('-j', '--jq-filter',
        type=str,
        metavar='jq_filter',
        default='.',
        help='Use jq(1) expression to filter the JSON data before diff')
    parser.add_argument('-l', '--left',
        action='store_true',
        help='Print the left-side response only')
    parser.add_argument('-r', '--right',
        action='store_true',
        help='Print the right-side response only')
    return parser.parse_args(sys.argv[1:])


async def request(url):
    async with ClientSession() as session:
        async with session.get(url) as response:
            result = {
                'version': 'HTTP/{}.{}'.format(response.version.major, response.version.minor),
                'status': response.status,
                'reason': response.reason,
                'content_type': response.content_type,
            }
            if response.content_type == 'application/json':
                result['json'] = await response.json()
            elif response.content_type.startswith('text/'):
                result['text'] = await response.text()
            else:
                result['bytes'] = await response.read()
            return result


async def jq_filter(input_data, jq_expr):
    """ Use jq(1) to filter the JSON data.
    """
    try:
        cmd = ['jq', '-S', jq_expr]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_data, stderr_data = await process.communicate(input=json.dumps(input_data).encode('utf-8'))
        if stderr_data:
            raise ApiDiffException("jq_filter failed", stderr_data.decode('utf-8'))
        return stdout_data.decode('utf-8')
    except PermissionError as e:
        raise ApiDiffException('It seems that jq(1) is not installed.') from e


async def print_unified_diff(a, b, fromfile='', tofile=''):
    sys.stdout.writelines(difflib.unified_diff(a.splitlines(keepends=True), b.splitlines(keepends=True), fromfile=fromfile, tofile=tofile))


async def run():
    args = await parseargs()

    tasks = []
    if args.left:
        tasks.append(asyncio.ensure_future(request(args.url_a)))
    elif args.right:
        tasks.append(asyncio.ensure_future(request(args.url_b)))
    else:
        tasks.append(asyncio.ensure_future(request(args.url_a)))
        tasks.append(asyncio.ensure_future(request(args.url_b)))

    if args.left or args.right:
        resp = (await asyncio.gather(*tasks))[0]
        print('Status:', resp['status'])
        print('Content-Type:', resp['content_type'])
        print()
        if 'text' in resp:
            print(resp.get('text'))
        if 'json' in resp:
            print(json.dumps(resp['json'], indent=4))
    else:
        resp_a, resp_b = await asyncio.gather(*tasks)

        if resp_a['status'] != resp_b['status']:
            a = '{} {} {}\n'.format(resp_a['version'], resp_a['status'], resp_a['reason'])
            b = '{} {} {}\n'.format(resp_b['version'], resp_b['status'], resp_b['reason'])
            await print_unified_diff(a, b, args.url_a, args.url_b)

        elif resp_a['content_type'] != resp_b['content_type']:
            a = 'Content-Type: {}\n'.format(resp_a['content_type'])
            b = 'Content-Type: {}\n'.format(resp_b['content_type'])
            await print_unified_diff(a, b, args.url_a, args.url_b)

        # Now we can safely assume that the content types of both sides are the same
        elif 'text' in resp_a:
            await print_unified_diff(resp_a['text'], resp_b['text'], args.url_a, args.url_b)

        elif 'json' in resp_a:
            json_a = await jq_filter(resp_a['json'], args.jq_filter)
            json_b = await jq_filter(resp_b['json'], args.jq_filter)
            await print_unified_diff(json_a, json_b, args.url_a, args.url_b)

        elif 'bytes' in resp_a:
            print('Binary data differ')

        else:
            ApiDiffException('Error: I dont know what to do. This is probably a bug')


def main():
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        pass
    except ApiDiffException as e:
        if os.getenv('APIDIFF_DEBUG'):
            traceback.print_exc()
        else:
            print('Error:', e, file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
