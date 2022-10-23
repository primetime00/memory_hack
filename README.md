# Mem Manip
## _Cross platform memory editor for games_

[![N|Solid](https://cldup.com/dTxpPi9lDf.thumb.png)](https://nodesource.com/products/nsolid)

[![Build Status](https://travis-ci.org/joemccann/dillinger.svg?branch=master)](https://travis-ci.org/joemccann/dillinger)

Mem Manip is a cross platform memory editor with a web based front-end.

- Search and modify memory regions.
- Save and load codes for use in games.
- Create scripts to enable trainer-like abilities.

## Features

- Memory searcher that can find 1, 2, 4 byte values as well as floating point values.
- Unknown value scanner to search for values not represented as numeric (life bars, timers, etc...)
- AOB (Array of bytes) heap scanner to help narrow down dynamic values.
- Code list that can store memory addresses and AOB values for reuse.
- Python script importer that can load scripts to enable trainer-like abilities.
- Web-based front-end that can be accessed from PC or phone.

## Screenshots

|                                             Code List                                             |                                              Search                                              |
|:-------------------------------------------------------------------------------------------------:|:------------------------------------------------------------------------------------------------:|
| ![snap_codes](https://github.com/primetime00/memory_hack/raw/master/docs/images/snap_codes.png) | ![snap_codes](https://github.com/primetime00/memory_hack/raw/master/docs/images/snap_search.png) | 

&NewLine;
&NewLine;

|                                                AOB                                                |                                              Scripts                                              |
|:-------------------------------------------------------------------------------------------------:|:-------------------------------------------------------------------------------------------------:|
| ![snap_codes](https://github.com/primetime00/memory_hack/raw/master/docs/images/snap_aob.png) | ![snap_codes](https://github.com/primetime00/memory_hack/raw/master/docs/images/snap_scripts.png) | 

Mem Manip uses a number of open source projects to work properly:

- [Falcon](https://github.com/falconry/falcon) - Minimalist ASGI/WSGI framework for building mission-critical REST APIs.
- [OnsenUI](https://onsen.io/) - A rich variety of UI components specially designed for mobile apps.
- [jQuery] - Fast, small, and feature-rich JavaScript library.
- [mem_edit](https://mpxd.net/code/jan/mem_edit) - Multi-platform memory editing library written in Python.

## Installation
### Windows
```
powershell -Command "(new-object System.Net.WebClient).DownloadFile('https://github.com/primetime00/memory_hack/raw/master/app/patches/win_install.py','install.py')"
```
Dillinger requires [Node.js](https://nodejs.org/) v10+ to run.

Install the dependencies and devDependencies and start the server.

```sh
cd dillinger
npm i
node app
```

For production environments...

```sh
npm install --production
NODE_ENV=production node app
```

## Plugins

Dillinger is currently extended with the following plugins.
Instructions on how to use them in your own application are linked below.

| Plugin | README |
| ------ | ------ |
| Dropbox | [plugins/dropbox/README.md][PlDb] |
| GitHub | [plugins/github/README.md][PlGh] |
| Google Drive | [plugins/googledrive/README.md][PlGd] |
| OneDrive | [plugins/onedrive/README.md][PlOd] |
| Medium | [plugins/medium/README.md][PlMe] |
| Google Analytics | [plugins/googleanalytics/README.md][PlGa] |

## Development

Want to contribute? Great!

Dillinger uses Gulp + Webpack for fast developing.
Make a change in your file and instantaneously see your updates!

Open your favorite Terminal and run these commands.

First Tab:

```sh
node app
```

Second Tab:

```sh
gulp watch
```

(optional) Third:

```sh
karma test
```

#### Building for source

For production release:

```sh
gulp build --prod
```

Generating pre-built zip archives for distribution:

```sh
gulp build dist --prod
```

## Docker

Dillinger is very easy to install and deploy in a Docker container.

By default, the Docker will expose port 8080, so change this within the
Dockerfile if necessary. When ready, simply use the Dockerfile to
build the image.

```sh
cd dillinger
docker build -t <youruser>/dillinger:${package.json.version} .
```

This will create the dillinger image and pull in the necessary dependencies.
Be sure to swap out `${package.json.version}` with the actual
version of Dillinger.

Once done, run the Docker image and map the port to whatever you wish on
your host. In this example, we simply map port 8000 of the host to
port 8080 of the Docker (or whatever port was exposed in the Dockerfile):

```sh
docker run -d -p 8000:8080 --restart=always --cap-add=SYS_ADMIN --name=dillinger <youruser>/dillinger:${package.json.version}
```

> Note: `--capt-add=SYS-ADMIN` is required for PDF rendering.

Verify the deployment by navigating to your server address in
your preferred browser.

```sh
127.0.0.1:8000
```

## License

MIT

**Free Software, Hell Yeah!**

[//]: # (These are reference links used in the body of this note and get stripped out when the markdown processor does its job. There is no need to format nicely because it shouldn't be seen. Thanks SO - http://stackoverflow.com/questions/4823468/store-comments-in-markdown-syntax)

   [dill]: <https://github.com/joemccann/dillinger>
   [git-repo-url]: <https://github.com/joemccann/dillinger.git>
   [john gruber]: <http://daringfireball.net>
   [df1]: <http://daringfireball.net/projects/markdown/>
   [markdown-it]: <https://github.com/markdown-it/markdown-it>
   [Ace Editor]: <http://ace.ajax.org>
   [node.js]: <http://nodejs.org>
   [Twitter Bootstrap]: <http://twitter.github.com/bootstrap/>
   [jQuery]: <http://jquery.com>
   [@tjholowaychuk]: <http://twitter.com/tjholowaychuk>
   [express]: <http://expressjs.com>
   [AngularJS]: <http://angularjs.org>
   [Gulp]: <http://gulpjs.com>

   [PlDb]: <https://github.com/joemccann/dillinger/tree/master/plugins/dropbox/README.md>
   [PlGh]: <https://github.com/joemccann/dillinger/tree/master/plugins/github/README.md>
   [PlGd]: <https://github.com/joemccann/dillinger/tree/master/plugins/googledrive/README.md>
   [PlOd]: <https://github.com/joemccann/dillinger/tree/master/plugins/onedrive/README.md>
   [PlMe]: <https://github.com/joemccann/dillinger/tree/master/plugins/medium/README.md>
   [PlGa]: <https://github.com/RahulHP/dillinger/blob/master/plugins/googleanalytics/README.md>
