"""
isicarchive.__main__

command line component

Supports the following flags:
 -a, --api-uri       ALTERNATIVE_API_URI
 -b, --base-url      ALTERNATIVE_BASE_URL
 -c, --cache-folder  CACHE_FOLDER
 -d, --debug
 -e, --endpoint      ENDPOINT_URI
 -i, --image         IMAGE_ID_FOR_DOWNLOAD
"""
# command line component
def main():

    # imports
    import argparse
    import json
    import netrc

    try:
        rp = True
        from IPython.lib.pretty import pretty
    except:
        rp = False
        import pprint
        pp = pprint.PrettyPrinter(indent=2)
    
    from . import func
    from .api import IsicApi
    from .vars import ISIC_API_URI, ISIC_BASE_URL
    from .version import __version__

    # prepare arg parser
    prog = 'python -m isicarchive'
    description = 'ISIC Archive API command line tool.'
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument('-a', '--api-uri',
        help='API URI, other than ' + ISIC_API_URI)
    parser.add_argument('-b', '--base-url',
        help='base URL, other than ' + ISIC_BASE_URL)
    parser.add_argument('-c', '--cache_folder',
        help='local folder with cached information')
    parser.add_argument('-d', '--debug', action='store_const', const=True,
        help='print all requests made to API (besides login)')
    parser.add_argument('-e', '--endpoint',
        help='fully qualified endpoint, e.g. /user/me')
    parser.add_argument('-i', '--image', nargs=2,
        help='download an image to local file')
    parser.add_argument('-j', '--json',
        help='JSON output filename (for endpoint syntax)')
    parser.add_argument('-p', '--params',
        help='endpoint parameters as key1=value1+key2=value2')
    parser.add_argument('-s', '--study',
        help='retrieve information about a study')
    parser.add_argument('--study-images', action='store_const', const=True,
        help='list study images')
    parser.add_argument('-u', '--username',
        help='username, if not in .netrc')
    parser.add_argument('--version', action='version', version=__version__,
        help='print version information')
    parser.add_argument('-x', '--extract',
        help='extract expression from endpoint response')
    options = parser.parse_args()

    # parse basic options
    api_uri = options.api_uri if options.api_uri else ISIC_API_URI
    hostname = options.base_url.lower() if options.base_url else ISIC_BASE_URL
    cache_folder = options.cache_folder if options.cache_folder else None
    debug = True if options.debug else False

    # check hostname, and access netrc
    if len(hostname) < 8 or hostname[0:4] != 'http':
        hostname = 'https://' + hostname
    if hostname[0:8] != 'https://':
        raise ValueError('Requires HTTPS protocol.')
    hostname_only = hostname[8:]
    netrc_o = netrc.netrc()
    netrc_tokens = netrc_o.authenticators(hostname_only)
    if netrc_tokens is None:
        username = None
        password = None
    else:
        username = netrc_tokens[0]
        password = netrc_tokens[2]
    if options.username:
        if username and username != options.username:
            username = options.username
            password = None
    
    # create API object
    api = IsicApi(
        username=username,
        password=password,
        hostname=hostname,
        api_uri=api_uri,
        cache_folder=cache_folder,
        debug=debug)

    # process GET params
    if options.params is None:
        params = None
    else:
        params = dict()
        ppairs = options.params.split('+')
        for pp in ppairs:
            pkv = pp.split('=')
            if len(pkv) == 2:
                params[pkv[0]] = pkv[1]

    # if a specific endpoint is requested, make request
    if not options.endpoint is None:
        jsonout = api.get(options.endpoint, params)

        # extract from endpoint
        if not options.extract is None:
            jsonout = func.getxattr(jsonout, options.extract)
            if jsonout is None:
                raise('Invalid extraction expression: '+ options.extract)

        # store as json
        if not options.json is None:
            jstr = json.dumps(jsonout)
            if options.json == 'stdout':
                print(jstr)
                return
            try:
                with open(options.json, 'w') as json_file:
                    json_file.write(jstr)
                return
            except:
                raise
        else:
            if isinstance(jsonout, str):
                print(jsonout)
            elif rp:
                print(pretty(jsonout))
            else:
                pp.pprint(jsonout)
            return

    # image download
    elif not options.image is None:
        try:
            api.image(options.image[0], save_as=options.image[1])
        except:
            raise

    # no explicit endpoint requested, print basic info
    if rp:
        print(pretty(api))
    else:
        print(api)
    
    # some additional endpoints supported outside of --endpoint
    if options.study_info:
        study = api.study(options.study_info)
        if rp:
            print(pretty(study))
        else:
            pp.pprint(study)
        if options.study_images:
            print('Images in study:')
            print('----------------')
            for image in study.images:
                print(image['name'] + ' (id: ' + image['_id'] + ') - ' +
                    str(image['meta']['acquisition']['pixelsX']) + ' by ' +
                    str(image['meta']['acquisition']['pixelsY']))


# only call if main
if __name__ == '__main__':
    main()
