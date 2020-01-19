#!/usr/bin/env python3
import cloudscraper
import time
import os
import sys
import re
import json
from zipfile import ZipFile


A_VERSION = "0.1.6"
LANG_CODE = "gb"


def dl(mangadex_id, raw_chapters, download_path):
	# grab manga info json from api
	manga = ""
	title = ""
	scraper = cloudscraper.create_scraper()
	try:
		r = scraper.get("https://mangadex.org/api/manga/{}/".format(mangadex_id))
		manga = json.loads(r.text)
	except (json.decoder.JSONDecodeError, ValueError) as err:
		print("CloudFlare error: {}".format(err))
		exit(1)

	try:
		title = manga["manga"]["title"]
	except KeyError:
		print("Please enter a MangaDex manga (not chapter) URL.")
		exit(1)
	print("\nTitle: {}".format(title))

	requested_chapters = gather_chapters(raw_chapters)
	# find out which are available to dl (in english for now)
	chaps_to_dl = []

	for chapter_id in manga["chapter"]:
		chapter_num = float(manga["chapter"][chapter_id]["chapter"])
		chapter_group = manga["chapter"][chapter_id]["group_name"]
		if chapter_num in requested_chapters and manga["chapter"][chapter_id]["lang_code"] == LANG_CODE:
			chaps_to_dl.append((str(chapter_num).replace(".0", ""), chapter_id, chapter_group))
	chaps_to_dl.sort()

	if len(chaps_to_dl) == 0:
		print("No chapters available to download!")
		exit(0)

	# get chapter(s) json
	print()
	for chapter_id in chaps_to_dl:
		print("Downloading chapter {}...".format(chapter_id[0]))
		r = scraper.get("https://mangadex.org/api/chapter/{}/".format(chapter_id[1]))
		chapter = json.loads(r.text)

		# get url list
		images = []
		server = chapter["server"]
		if "mangadex.org" not in server:
			server = "https://mangadex.org{}".format(server)
		hashcode = chapter["hash"]
		for page in chapter["page_array"]:
			images.append("{}{}/{}".format(server, hashcode, page))

		# download images
		dest_folder = ""
		pattern = re.compile(r'([^\s\w]|_)+')
		sanitized_title = pattern.sub('', title)
		manga_archive_name = "{0} - Chapter {1}.cbz".format(sanitized_title, chapter_id[0])
		page_num = 1
		for img in images:
			_, extension = os.path.splitext(img)
			filename = str(page_num).zfill(3) + extension
			dest_folder = os.path.join("/tmp", "download", "{0}_c{1}".format(mangadex_id, chapter_id[0]))
			if not os.path.exists(dest_folder):
				os.makedirs(dest_folder)
			outfile = os.path.join(dest_folder, filename)

			r = scraper.get(img)
			if r.status_code == 200:
				with open(outfile, 'wb') as f:
					f.write(r.content)
			else:
				print("Encountered Error {} when downloading.".format(r.code))

			print(" Downloaded page {}.".format(re.sub("\\D", "", filename)))
			page_num += 1
		files = get_all_file_paths(dest_folder)
		create_cbz_archive(files, manga_archive_name, download_path)


def gather_chapters(raw_chapters):
	requested_chapters = []
	chap_list = raw_chapters
	chap_list = [s for s in chap_list.split(',')]
	for s in chap_list:
		if "-" in s:
			r = [int(float(n)) for n in s.split('-')]
			s = list(range(r[0], r[1]+1))
		else:
			s = [float(s)]
		requested_chapters.extend(s)
	return requested_chapters


def create_cbz_archive(file_paths, archive_name, download_path):
	base_bath = os.getcwd()
	if download_path != "":
		base_bath = download_path
	with ZipFile(os.path.join(base_bath, archive_name), 'w') as z:
		for file in file_paths:
			z.write(file)


def get_all_file_paths(directory):
	file_paths = []
	for root, directories, files in os.walk(directory):
		for filename in files:
			filepath = os.path.join(root, filename)
			file_paths.append(filepath)
	return file_paths


if __name__ == "__main__":
	url = sys.argv[1]
	chapters = sys.argv[2]
	download_path = ""
	if len(sys.argv) == 4:
		download_path = sys.argv[3]
	manga_id = re.search("[0-9]+", url).group(0)
	dl(manga_id, chapters, download_path)

