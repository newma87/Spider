#!/bin/bash
source ~/.bash_profile
workon spider_env

gnome-terminal -x sh -c "python dbserver.py; bash"
gnome-terminal -x sh -c "python downloader.py 4; bash"
gnome-terminal -x sh -c "python spider.py 4; bash"

