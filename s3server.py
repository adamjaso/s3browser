#!/usr/bin/env python3
import os
import sys
import boto3
from botocore import errorfactory
from flask import Flask, Response, redirect, request

S3_BUCKET = os.getenv('S3_BUCKET')
s3 = boto3.client('s3')
app = Flask(__name__)
app.debug = False


def get_s3_url(name):
    url = s3.generate_presigned_url(
        Params={'Bucket': S3_BUCKET, 'Key': name},
        ClientMethod='get_object',
        HttpMethod='GET',
        ExpiresIn=600,
    )
    return url


@app.route("/")
def list_objects():
    objects = s3.list_objects_v2(Bucket=S3_BUCKET, Delimiter="/")
    return show_objects(objects)


@app.route("/_watch/<path:key>")
def video_player(key):
    parts = key.split("/")
    series = "/".join(parts[:-1])
    episode = parts[-1]
    objects = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=series + "/", Delimiter="/")
    return show_videos(objects, key)


@app.route("/_redirect/<path:key>")
def redirect_object(key):
    url = get_s3_url(key)
    return redirect(url)


@app.route("/<path:key>")
def view_object(key):
    if key[-1] == '/':
        objects = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=key, Delimiter="/")
        return show_objects(objects)

    try:
        body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"]
    except s3.exceptions.NoSuchKey:
        return "Object not found", 404

    def read_body():
        buf = body.read(64 * 1024)
        while buf:
            yield buf
            buf = body.read(64 * 1024)

    return Response(read_body(), headers={"Content-Type": "text/plain"})


def show_objects(objects):
    directories = objects.get('CommonPrefixes', [])
    files = objects.get('Contents', [])
    html = [f"""<!DOCTYPE html>
<html>
<head>
<title>{S3_BUCKET}</title>
<style>
td {{ padding: 5px 10px; }}
</style>
</head>
<body>
<h3><a href="/">Home</a></h3>
<table border="1">
<thead>
<tr>
<td>Last Modified</td>
<td>Size</td>
<td>Download</td>
<td>View</td>
<td>Name</td>
</tr>
</thead>
<tbody>"""]
    for item in directories:
        url = get_s3_url(item['Prefix'])
        html.append(f"""
<tr>
<td><!-- no last modified --></td>
<td><!-- no size --></td>
<td><a href="/_watch/{item["Prefix"]}">Watch</a></td>
<td><a href="/{item["Prefix"]}">View</a></td>
<td>{item["Prefix"]}</td>
</tr>
""")
    for item in files:
        html.append(f"""
<tr>
<td>{item["LastModified"]}</td>
<td>{item["Size"]}</td>
<td><a target="_blank" href="/_redirect/{item["Key"]}">Download</a></td>
<td><a target="_blank" href="/{item["Key"]}">View</a></td>
<td>{item["Key"]}</td>
</tr>
""")
    html.append("""
</tbody>
</table>
</body></html>""")
    return "\n".join(html)


def show_videos(objects, prefix):
    files = objects.get('Contents', [])
    back_url = os.path.dirname(os.path.dirname(prefix[:-1]))
    try:
        curr_index, _ = next((i, val["Key"]) for i, val in enumerate(files) if val["Key"].endswith(prefix))
    except StopIteration:
        curr_index = 0
    if curr_index > 0:
        prev_url = files[curr_index - 1]["Key"]
    else:
        prev_url = "javascript:void(0);"
    if curr_index < len(files) - 1:
        next_url = files[curr_index + 1]["Key"]
    else:
        next_url = "javascript:void(0);"
    title = os.path.basename(prefix)
    html = []
    html.append(f"""<!DOCTYPE html>
<html>
<head>
<title>{title}</title>
<link rel="icon" href="data:,">
</head>
<body>
<div>
<video id="player" controls="true" type="video/mp4" autoplay="autoplay" width="100%" height="auto"></video>
<div style="margin:20px 10px">
<a href="/{back_url}/">Home</a> |
<a href="/_watch/{prev_url}">Previous Episode</a> |
<a href="/_watch/{next_url}">Next Episode</a> |
</div>
    """)
    for item in files:
        #s3_url = get_s3_url(item["Key"])
        s3_name = os.path.basename(item["Key"])
        html.append(f"""
<div><a class="video_url" href="{s3_name}">{s3_name}</a></div>
        """)
    html.append("""
</div>
<script>
  window.onload = function() {
    var video = document.getElementById("player");
    var anchors = document.getElementsByClassName("video_url");
    var baseLink = window.location.href.split("/").slice(0, -1).join("/");
    var currLink = window.location.href;
    if (currLink.split("/").pop() == "" && localStorage[baseLink]) {
        window.location = localStorage[baseLink];
        return;
    }
    var currIndex = -1;
    for (var i = 0; i < anchors.length; i++) {
        if (currIndex == -1 && anchors[i].href == currLink) currIndex = i;
    }
    if (!currLink || currIndex == -1) {
        window.location = anchors[0].href;
        return;
    }
    var nextLink;
    if (currIndex + 1 < anchors.length) nextLink = anchors[currIndex + 1].href;
    var playTimeout;
    window.addEventListener("keydown", function(e) {
        if (e.keyCode == 32 && e.target == document.body) {
            togglePlay(); // when we press " " play/pause
            e.preventDefault();
            return false;
        }
        return true;
    });
    window.addEventListener("keyup", function(e) {
      if (e.keyCode == 70) { // when we press "f" toggle fullscreen
        fullscreen();
      } else if (e.keyCode == 74) { // when we press "j" go backward 10s
        video.currentTime -= 10;
      } else if (e.keyCode == 76) { // when we press "l" go forward 10s
        video.currentTime += 10;
      }
      e.preventDefault();
      return false;
    });
    video.addEventListener("error", function(e) {
        console.log(e);
        if (confirm("An error occurred. Do you want to start the next episode?")) {
            window.location = nextLink;
        }
    });
    function togglePlay() {
      video.paused ? video.play() : video.pause();
    }
    function fullscreen() {
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        video.requestFullscreen();
      }
    }
    function getVideoURL(url) {
      return url.replace(/\/_watch\//, "/_redirect/");
    }
    var switching = false;
    video.ontimeupdate = () => {
      var remaining = video.duration - video.currentTime;
      if (!switching && remaining < 15) {
        switching = true;
        console.log("Remaining threshold crossed. Loading next...");
        if (nextLink) {
            window.location = nextLink;
        }
      }
    };
    localStorage[baseLink] = currLink;
    video.src = getVideoURL(currLink);
    video.play();
  };
</script>
</body>
</html>""")
    return "\n".join(html)


def main():
    app.run(host="0.0.0.0", port=int(os.getenv('PORT', 8080)))


if __name__ == '__main__':
    main()
