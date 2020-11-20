#!/usr/bin/env python3
import os
import sys
import boto3
from botocore import errorfactory
from flask import Flask, Response, redirect

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
<td><!-- no download url --></td>
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


def main():
    app.run(host="0.0.0.0", port=int(os.getenv('PORT', 8080)))


if __name__ == '__main__':
    main()
