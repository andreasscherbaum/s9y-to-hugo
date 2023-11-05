#!/usr/bin/env python3

import os
import sys
import re
import pathlib
import shutil
import logging
import argparse
from datetime import datetime
from dateutil import tz
from dateutil.tz import *
import time
# https://github.com/matthewwithanm/python-markdownify
import markdownify
import subprocess
import frontmatter
from pprint import pprint
import io
from bs4 import BeautifulSoup
import urllib.parse


# start with 'info', can be overriden by '-q' later on
logging.basicConfig(level = logging.INFO,
		    format = '%(levelname)s: %(message)s')



#######################################################################
# Config class

class Config:

    def __init__(self):
        self.__cmdline_read = 0
        self.__configfile_read = 0
        self.arguments = False
        self.argument_parser = False
        self.configfile = False
        self.config = False
        self.output_help = True

        if (os.environ.get('HOME') is None):
            logging.error("$HOME is not set!")
            sys.exit(1)
        if (os.path.isdir(os.environ.get('HOME')) is False):
            logging.error("$HOME does not point to a directory!")
            sys.exit(1)


    # config_help()
    #
    # flag if help shall be printed
    #
    # parameter:
    #  - self
    #  - True/False
    # return:
    #  none
    def config_help(self, config):
        if (config is False or config is True):
            self.output_help = config
        else:
            print("")
            print("invalid setting for config_help()")
            sys.exit(1)


    # print_help()
    #
    # print the help
    #
    # parameter:
    #  - self
    # return:
    #  none
    def print_help(self):
        if (self.output_help is True):
            self.argument_parser.print_help()


    # parse_parameters()
    #
    # parse commandline parameters, fill in array with arguments
    #
    # parameter:
    #  - self
    # return:
    #  none
    def parse_parameters(self):
        parser = argparse.ArgumentParser(description = 'Convert S9y blog to Hugo',
                                         add_help = False)
        self.argument_parser = parser
        parser.add_argument('--help', default = False, dest = 'help', action = 'store_true', help = 'show this help')
        parser.add_argument('--dbtype', dest = 'dbtype', choices=['pg', 'mysql'], help = 'type of database (pg for PostgreSQL, mysql for MySQL/MariaDB)')
        parser.add_argument('--dbhost', default = '', dest = 'dbhost', help = 'database host')
        parser.add_argument('--dbuser', default = '', dest = 'dbuser', help = 'database user')
        parser.add_argument('--dbpass', default = '', dest = 'dbpass', help = 'database pass')
        parser.add_argument('--dbname', default = '', dest = 'dbname', help = 'database name')
        parser.add_argument('--dbport', default = '5432', dest = 'dbport', help = 'database port')
        parser.add_argument('--dbprefix', default = '', dest = 'dbprefix', help = 'S9Y database prefix', required = True)
        # run Hugo from subdirectory: https://discourse.gohugo.io/t/make-home-to-be-subdirectory/4345/6
        parser.add_argument('--webprefix', default = '/', dest = 'webprefix', help = 'Hugo web prefix')
        parser.add_argument('--oldwebprefix', default = '/', dest = 'oldwebprefix', help = 'S9y web prefix')
        parser.add_argument('--targetdir', default = '', dest = 'targetdir', help = 'targetdir for Hugo Markdown files (Hugo base directory)')
        parser.add_argument('--imagedir', default = '', dest = 'imagedir', help = 'base directory with images from old blog (must match path in blog postings)')
        # avoid using Hugo aliases, which generate clutter
        # https://gohugo.io/content-management/urls/#aliases
        parser.add_argument('--rewritefile', default = '', dest = 'rewritefile', help = 'file for adding URL rewrites from old to new postings')
        parser.add_argument('--rewritetype', default = '', choices=['apache2'], dest = 'rewritetype', help = 'type of rewrite file (currently only Apache2 is supported)')
        # https://gohugo.io/content-management/organization/
        parser.add_argument('--use-bundles', default = False, dest = 'use_bundles', action = 'store_true', help = 'use Hugo bundles instead of single Markdown files')
        parser.add_argument('--remove-s9y-id', default = False, dest = 'remove_s9y_id', action = 'store_true', help = 'remove the S9Y id from URL')
        parser.add_argument('--add-date-to-url', default = False, dest = 'add_date_to_url', action = 'store_true', help = 'add the posting date to the URL')
        parser.add_argument('--ignore-post', dest = 'ignore_post', action = 'append', help = 'ignore this posting (URL) during migration (can be specified multiple times)')
        parser.add_argument('--ignore-picture-errors', dest = 'ignore_picture_errors', action = 'append', help = 'ignore picture errors in this posting (URL) during migration (can be specified multiple times)')
        parser.add_argument('--use-utc', default = False, dest = 'use_utc', action = 'store_true', help = 'use UTC time instead of local time')
        parser.add_argument('--write-html', default = False, dest = 'write_html', action = 'store_true', help = 'write a copy of the original HTML to a .html file')
        parser.add_argument('--archive-link', default = '', dest = 'archive_link', help = 'use this link for archive redirects (othewise webprefix is used)')
        parser.add_argument('--add-year-link-to-archive', default = False, dest = 'add_year_link_to_archive', action = 'store_true', help = 'add redirects to a specific year for the archive links')
        parser.add_argument('--hugo-bin', default = '', dest = 'hugo_bin', help = 'use this binary as Hugo binary (otherwise auto-detected)')
        # store_true: store "True" if specified, otherwise store "False"
        # store_false: store "False" if specified, otherwise store "True"
        parser.add_argument('-v', '--verbose', default = False, dest = 'verbose', action = 'store_true', help = 'be more verbose')
        parser.add_argument('-q', '--quiet', default = False, dest = 'quiet', action = 'store_true', help = 'run quietly')


        # parse parameters
        args = parser.parse_args()

        if (args.help is True):
            self.print_help()
            sys.exit(0)

        if (args.verbose is True and args.quiet is True):
            self.print_help()
            print("")
            print("Error: --verbose and --quiet can't be set at the same time")
            sys.exit(1)

        if (args.verbose is True):
            logging.getLogger().setLevel(logging.DEBUG)

        if (args.quiet is True):
            logging.getLogger().setLevel(logging.ERROR)

        if (args.dbtype == "mysql"):
            print("MySQL/MariaDB support is currently not implemented")
            sys.exit(1)

        if (args.targetdir == ""):
            self.print_help()
            print("")
            print("Error: targetdir is required")
            sys.exit(1)

        if (not os.path.exists(args.targetdir) or not os.access(args.targetdir, os.W_OK)):
            self.print_help()
            print("")
            print("Error: targetdir must exist and must be writable")
            print("Directory: " + args.targetdir)
            sys.exit(1)

        if (os.path.realpath(args.targetdir) != args.targetdir):
            args.targetdir = os.path.realpath(args.targetdir)
            logging.debug("Setting target dir to absolute path: " + args.targetdir)

        contentdir = os.path.join(args.targetdir, "content")
        if (not os.path.exists(contentdir) or not os.access(contentdir, os.W_OK)):
            self.print_help()
            print("")
            print("Error: targetdir must be a Hugo directory")
            print("Directory: " + contentdir)
            sys.exit(1)

        if (args.rewritefile != ""):
            if (os.path.exists(args.rewritefile)):
                self.print_help()
                print("")
                print("Error: rewritefile must not exist")
                sys.exit(1)

            if (args.rewritetype == ''):
                self.print_help()
                print("")
                print("Error: rewritetype must be specified when rewritefile is selected")
                sys.exit(1)

        if (args.imagedir != ""):
            # it's possible that the old blog has no images at all
            if (not os.path.exists(args.imagedir)):
                self.print_help()
                print("")
                print("Error: imagedir must exist when specified")
                sys.exit(1)
            if (os.path.realpath(args.imagedir) != args.imagedir):
                args.imagedir = os.path.realpath(args.imagedir)
                logging.debug("Setting image dir to absolute path: " + args.imagedir)

        if (args.webprefix[-1] != '/'):
            args.webprefix += '/'
            logging.debug("Add / suffix for web prefix, now: " + args.webprefix)

        if (args.oldwebprefix[-1] != '/'):
            args.oldwebprefix += '/'
            logging.debug("Add / suffix for old web prefix, now: " + args.oldwebprefix)

        if (args.hugo_bin != ""):
            if (not os.path.exists(args.hugo_bin)):
                self.print_help()
                print("")
                print("Error: hugo-bin must exist when specified")
                sys.exit(1)
            if (not os.access(args.hugo_bin, os.X_OK)):
                self.print_help()
                print("")
                print("Error: hugo-bin must be executable")
                sys.exit(1)
        else:
            # find binary
            hugo = shutil.which("hugo")
            if (hugo is None):
                self.print_help()
                print("")
                print("Error:no Hugo executable found")
                sys.exit(1)
            args.hugo_bin = hugo
            logging.debug("Choosing {bin} as Hugo executable".format(bin = hugo))

        if (args.archive_link == ""):
            if (args.add_year_link_to_archive is True):
                print("Can't use --add-year-link-to-archive without --archive-link")
                sys.exit(1)
            # use webroot as redirect link
            args.archive_link = args.webprefix

        self.__cmdline_read = 1
        self.arguments = args
        logging.debug("Commandline arguments successfuly parsed")

        return

# end Config class
#######################################################################



#######################################################################
# DatabasePG class

class DatabasePG:
    # avoid importing the module in the global class space
    # this way, it's only loaded if someone selects the PostgreSQL driver
    # otherwise it must be installed all the time, even if someone doesn't need it
    import psycopg2
    from psycopg2.extras import RealDictCursor


    def __init__(self, config):
        self.config = config
        self.dbprefix = self.config.arguments.dbprefix

        try:
            connect_data = []

            if (len(self.config.arguments.dbhost) > 0):
                connect_data.append("host='{host}'".format(host = self.config.arguments.dbhost))

            if (len(self.config.arguments.dbname) > 0):
                connect_data.append("dbname='{host}'".format(host = self.config.arguments.dbname))

            if (len(self.config.arguments.dbuser) > 0):
                connect_data.append("user='{host}'".format(host = self.config.arguments.dbuser))

            if (len(self.config.arguments.dbport) > 0):
                connect_data.append("port='{host}'".format(host = self.config.arguments.dbport))

            if (len(self.config.arguments.dbpass) > 0):
                connect_data.append("password='{host}'".format(host = self.config.arguments.dbpass))

            connect_string = " ".join(connect_data)

            # the self.psycopg2 is required, because the module lives only in this class
            conn = self.psycopg2.connect(connect_string)
        except self.psycopg2.DatabaseError as e:
            print('Error %s' % e) 
            sys.exit(1)

        self.connection = conn


    # run_query()
    #
    # execute a database query without parameters
    #
    # parameter:
    #  - self
    #  - query
    # return:
    #  none
    def run_query(self, query):
        cur = self.connection.cursor()
        cur.execute(query)
        self.connection.commit()


    # execute_one()
    #
    # execute a database query with parameters, return single result
    #
    # parameter:
    #  - self
    #  - query
    #  - list with parameters
    # return:
    #  - result
    def execute_one(self, query, param):
        cur = self.connection.cursor(cursor_factory = self.psycopg2.extras.DictCursor)

        cur.execute(query, param)
        result = cur.fetchone()

        self.connection.commit()
        return result


    # execute_query()
    #
    # execute a database query with parameters, return result set
    #
    # parameter:
    #  - self
    #  - query
    #  - list with parameters
    # return:
    #  - result set
    def execute_query(self, query, param):
        cur = self.connection.cursor(cursor_factory = self.psycopg2.extras.DictCursor)

        cur.execute(query, param)
        result = cur.fetchall()

        self.connection.commit()
        return result


    def fetch_table(self, table, order_by = None):
        query = 'SELECT * FROM "{p}_{t}"'.format(p = self.dbprefix, t = table)
        if (order_by is not None):
            query += ' ORDER BY "{o}"'.format(o = order_by)
        #print(query)

        return self.execute_query(query, [])


    def authors(self):
        authors = self.fetch_table('authors', 'authorid')

        return authors


    def categories(self):
        categories = self.fetch_table('category', 'categoryid')

        return categories


    def entry_categories(self):
        entry_categories = self.fetch_table('entrycat', 'entryid')

        return entry_categories


    def tags(self):
        tags = self.fetch_table('entrytags', 'entryid')

        return tags


    def permalinks(self):
        permalinks = self.fetch_table('permalinks', 'entry_id')

        return permalinks


    def entries(self):
        entries = self.fetch_table('entries', 'id')

        return entries


    def number_entries_by_author(self, authorid):
        query = 'SELECT COUNT(*) AS count FROM "{p}_entries" WHERE authorid = %s'.format(p = self.dbprefix)
        result = self.execute_one(query, [str(authorid)])

        return result[0]


    def number_entries_by_category(self, categoryid):
        query = 'SELECT COUNT(*) AS count FROM "{p}_entrycat" WHERE categoryid = %s'.format(p = self.dbprefix)
        result = self.execute_one(query, [str(categoryid)])

        return result[0]


    def number_entries_by_tag(self, tag):
        query = 'SELECT COUNT(*) AS count FROM "{p}_entrytags" WHERE tag = %s'.format(p = self.dbprefix)
        result = self.execute_one(query, [str(tag)])

        return result[0]


    def s9y_config_entry(self, entry):
        query = "SELECT value FROM serendipity_config where authorid = 0 and name = %s"
        result = self.execute_one(query, [entry])

        return result[0]


# end DatabasePG class
#######################################################################



#######################################################################
# Database class

class Database:

    def __init__(self, config):
        self.config = config
        self.dbtype = self.config.arguments.dbtype

        if (self.dbtype == "pg"):
            logging.debug("Selecting PostgreSQL driver")
            self.connection = DatabasePG(config)


    def test(self):
        if (self.dbtype == "pg"):
            self.connection.test()


    def execute_query(self, query, param):
        return self.connection.execute_query(query, param)


    def authors(self):
        return self.connection.authors()


    def categories(self):
        return self.connection.categories()


    def entry_categories(self):
        return self.connection.entry_categories()


    def tags(self):
        return self.connection.tags()


    def permalinks(self):
        return self.connection.permalinks()


    def entries(self):
        return self.connection.entries()


    def number_entries_by_author(self, authorid):
        return self.connection.number_entries_by_author(authorid)


    def number_entries_by_category(self, categoryid):
        return self.connection.number_entries_by_category(categoryid)


    def number_entries_by_tag(self, tag):
        return self.connection.number_entries_by_tag(tag)


    def s9y_config_entry(self, entry):
        return self.connection.s9y_config_entry(entry)


# end Database class
#######################################################################




#######################################################################
# Migration class

class Migration:

    def __init__(self, config, db):
        self.config = config
        self.db = db

        self.authors_by_id = {}
        self.authors_by_username = {}
        self.categories_by_id = {}
        self.categories_by_name = {}
        self.categories_by_id_new = {}
        self.entry_categories_by_category = {}
        self.entry_categories_by_entry = {}
        self.tags_by_id = {}
        self.tags_by_name = {}
        self.tags_by_id_new = {}
        self.permalinks_by_id = {}
        self.seen_new_urls = {}
        self.parsed_hugo_config = {}
        self.use_categories = False
        self.use_tags = False
        self.use_authors = False
        self.redirect_links_seen = {}

        self.calculate_tz_offset()
        self._get_hugo_config()


    def calculate_tz_offset(self):
        # problem description: the webserver either runs on UTC time, or an abritrary time zone
        # but we don't know if the server uses the same time as the system which runs the migration
        # and there is no way to find out, because S9y doesn't store the actual time zone
        # all it stores is the difference between author time (global) and the server, in
        # hours, not even taking into account that some countries use :30 and such
        # there is the --use-utc option which lets the migration run on UTC time, but beyond
        # that we have to trust that the migration runs in the same time zone as the S9y blog

        # $serendipity[‘useServerOffset’]: Boolean whether the timezone of the server and the authors differs
        # $serendipity[‘serverOffsetHours’]: How many hours timezone difference are between server and authors
        q1 = "SELECT value FROM serendipity_config where authorid = 0 and name = 'useServerOffset'"
        r1 = self.db.execute_query(q1, [])
        if (r1[0]['value'] == 'true'):
            self.useServerOffset = True
        elif (r1[0]['value'] == 'false'):
            self.useServerOffset = False
        else:
            self.useServerOffset = False

        q2 = "SELECT value FROM serendipity_config where authorid = 0 and name = 'serverOffsetHours'"
        r2 = self.db.execute_query(q2, [])
        self.useServerOffset = r2[0]['value']


    # this emulates parts of the serendipity_makeFilename() function from S9Y
    # https://github.com/s9y/Serendipity/blob/master/include/functions_permalinks.inc.php
    def _serendipity_makeFilename(self, string):
        replacements = {'🇦': 'A',
                        '🇧': 'B',
                        '🇨': 'C',
                        '🇩': 'D',
                        '🇪': 'E',
                        '🇫': 'F',
                        '🇬': 'G',
                        '🇭': 'H',
                        '🇮': 'I',
                        '🇯': 'J',
                        '🇰': 'K',
                        '🇱': 'L',
                        '🇲': 'M',
                        '🇳': 'N',
                        '🇴': 'O',
                        '🇵': 'P',
                        '🇶': 'Q',
                        '🇷': 'R',
                        '🇸': 'S',
                        '🇹': 'T',
                        '🇺': 'U',
                        '🇻': 'V',
                        '🇼': 'W',
                        '🇽': 'X',
                        '🇾': 'Y',
                        '🇿': 'Z'}
        replaced = [replacements.get(char, char) for char in str(string)]
        string = ''.join(replaced)

        replacements = {' ': '-',
                        '%': '%25',
                        'Ä': 'AE',
                        'ä': 'ae',
                        'Ö': 'OE',
                        'ö': 'oe',
                        'Ü': 'UE',
                        'ü': 'ue',
                        'ß': 'ss',
                        'é': 'e',
                        'è': 'e',
                        'ê': 'e',
                        'í': 'i',
                        'ì': 'i',
                        'î': 'i',
                        'á': 'a',
                        'à': 'a',
                        'â': 'a',
                        'å': 'a',
                        'ó': 'o',
                        'ò': 'o',
                        'ô': 'o',
                        'õ': 'o',
                        'ú': 'u',
                        'ù': 'u',
                        'û': 'u',
                        'ç': 'c',
                        'Ç': 'C',
                        'ñ': 'n',
                        'ý': 'y'}
        replaced = [replacements.get(char, char) for char in string]
        string = ''.join(replaced)

        replacements = {' ': '_',
                        '&': '%25',
                        'Ä': 'AE',
                        'ä': 'ae',
                        'Ö': 'OE',
                        'ö': 'oe',
                        'Ü': 'UE',
                        'ü': 'ue',
                        'ß': 'ss',
                        'é': 'e',
                        'è': 'e',
                        'ê': 'e',
                        'í': 'i',
                        'ì': 'i',
                        'î': 'i',
                        'á': 'a',
                        'à': 'a',
                        'â': 'a',
                        'å': 'a',
                        'ó': 'o',
                        'ò': 'o',
                        'ô': 'o',
                        'õ': 'o',
                        'ú': 'u',
                        'ù': 'u',
                        'û': 'u',
                        'ç': 'c',
                        'Ç': 'C',
                        'ñ': 'n',
                        'ý': 'y',
                        '/': ''}
        replaced = [replacements.get(char, char) for char in string]
        string = ''.join(replaced)

        # that's buried somewhere in serendipity_makeFilename() in S9y
        string = string.replace("'", "")

        return string


    def hugo_path(self, *names):
        path = self.config.arguments.targetdir
        for p in list(names):
            path = os.path.join(path, p)
        return path
        

    def ensure_directory_exists(self, name):
        logging.debug("Ensure directory exists: {d}".format(d = name))
        os.makedirs(name, exist_ok = True)


    def file_exists(self, name):
        logging.debug("Check if file exists: {f}".format(f = name))
        return os.path.exists(name)


    def authors(self):
        logging.debug("Migrating authors")
        authorsdir = self.hugo_path('data', 'authors')
        self.ensure_directory_exists(authorsdir)
        authors = self.db.authors()

        # number of entries per page
        fetchlimit = int(self.db.s9y_config_entry('fetchLimit'))
        if (fetchlimit < 1):
            logging.error("fetchLimit in S9y is invalid!")
            sys.exit(1)

        #print(authors)
        for a in authors:
            self.authors_by_id[a['authorid']] = a
            self.authors_by_username[a['username']] = a
            author_file = self.hugo_path(authorsdir, a['username'] + '.yml')
            if (not self.file_exists(author_file)):
                logging.info("Author ({a}) does not yet have a file".format(a = a['username']))
                file_content = "Name: {name}".format(name = a['realname']) + "\n"
                file_content += "OriginalID: {id}".format(id = a['authorid']) + "\n"
                file_content += "Username: {id}".format(id = a['username']) + "\n"
                with open(author_file, 'w') as f:
                    f.write(file_content)
            else:
                # not touching existing file
                logging.debug("Author ({a}) already has a file".format(a = a['username']))

            author_url_old = "{owp}authors/{id}-{name}".format(owp = self.config.arguments.oldwebprefix,
                                                               id = a['authorid'],
                                                               name = self._serendipity_makeFilename(a['realname']))
            author_name_new = self._sanitize_url_string(a['username']).lower()
            author_url_new = "{nwp}authors/{name}/".format(nwp = self.config.arguments.webprefix,
                                                          name = author_name_new)

            if (self.use_authors):
                self._write_rewrite_file(author_url_old, author_url_new, '')
            else:
                # author taxonomy is not used, but the old URLs exist
                # redirect this to the main page
                self._write_rewrite_file(author_url_old, self.config.arguments.webprefix, '')

            # S9y creates listing pages for all author postings in the format:
            # /authors/<author>/P<number>.html
            # need to know how many of such pages exist
            number_entries = self.db.number_entries_by_author(a['authorid'])
            number_pages = int(number_entries / fetchlimit) + 1
            for n in range(1, number_pages + 1):
                author_url_old = "{owp}authors/{id}-{name}/P{n}.html".format(owp = self.config.arguments.oldwebprefix,
                                                                             id = a['authorid'],
                                                                             name = self._serendipity_makeFilename(a['realname']),
                                                                             n = n)
                # redirect everything to the main page
                self._write_rewrite_file(author_url_old, self.config.arguments.webprefix, '')


    def _sanitize_url_string(self, string):
        new_string = string.replace('/', '').replace(' ', '-')

        return new_string


    def categories(self):
        logging.debug("Reading categories")
        categories = self.db.categories()
        #print(categories)

        # number of entries per page
        fetchlimit = int(self.db.s9y_config_entry('fetchLimit'))
        if (fetchlimit < 1):
            logging.error("fetchLimit in S9y is invalid!")
            sys.exit(1)

        for c in categories:
            if (c['category_name'] == '/'):
                continue

            self.categories_by_id[c['categoryid']] = c
            self.categories_by_name[c['category_name']] = c

            category_name = c['category_name']
            category_name_old = self._serendipity_makeFilename(category_name)
            category_url_old = "{owp}categories/{id}-{name}".format(owp = self.config.arguments.oldwebprefix,
                                                                    id = c['categoryid'],
                                                                    name = category_name_old)

            category_name_new = self._sanitize_url_string(category_name).lower()
            category_url_new = "{nwp}categories/{name}/".format(nwp = self.config.arguments.webprefix,
                                                               name = category_name_new)

            if (self.use_categories):
                self._write_rewrite_file(category_url_old, category_url_new, '')
            else:
                # category taxonomy is not used, but the old URLs exist
                # redirect this to the main page
                self._write_rewrite_file(category_url_old, self.config.arguments.webprefix, '')

            # generate redirects for the RSS feed
            # it's ".rss" in S9y, and "index.xml" in Hugo, plus different pathnames
            category_feed_name_old = self._serendipity_makeFilename(category_name)
            category_feed_url_old = "{owp}feeds/categories/{id}-{name}.rss".format(owp = self.config.arguments.oldwebprefix,
                                                                                   id = c['categoryid'],
                                                                                   name = category_name_old)

            category_feed_name_new = self._sanitize_url_string(category_name).lower()
            category_feed_url_new = "{nwp}categories/{name}/index.xml".format(nwp = self.config.arguments.webprefix,
                                                                              name = category_name_new)

            if (self.use_categories):
                self._write_rewrite_file(category_feed_url_old, category_feed_url_new, '')
            else:
                # category taxonomy is not used, but the old URLs exist
                # redirect this to the main page
                self._write_rewrite_file(category_feed_url_old, self.config.arguments.webprefix, '')

            self.categories_by_id_new[c['categoryid']] = category_name_new

            # S9y creates listing pages for all categories in the format:
            # /categories/<category>/P<number>.html
            # need to know how many of such pages exist
            number_entries = self.db.number_entries_by_category(c['categoryid'])
            number_pages = int(number_entries / fetchlimit) + 1
            for n in range(1, number_pages + 1):
                category_url_old = "{owp}categories/{id}-{name}/P{n}.html".format(owp = self.config.arguments.oldwebprefix,
                                                                                  id = c['categoryid'],
                                                                                  name = category_name_old,
                                                                                  n = n)
                if (self.use_categories):
                    self._write_rewrite_file(category_url_old, category_url_new, '')
                else:
                    # category taxonomy is not used, but the old URLs exist
                    # redirect this to the main page
                    self._write_rewrite_file(category_url_old, self.config.arguments.webprefix, '')


    def entry_categories(self):
        logging.debug("Reading entry categories")
        entry_categories = self.db.entry_categories()
        #print(entry_categories)
        for e in entry_categories:
            if (e['entryid'] not in self.entry_categories_by_entry):
                self.entry_categories_by_entry[e['entryid']] = []
            self.entry_categories_by_entry[e['entryid']].append(e['categoryid'])

            if (e['categoryid'] not in self.entry_categories_by_category):
                self.entry_categories_by_category[e['categoryid']] = []
            self.entry_categories_by_category[e['categoryid']].append(e['entryid'])


    def tags(self):
        logging.debug("Reading tags")
        tags = self.db.tags()
        #print(tags)

        # number of entries per page
        fetchlimit = int(self.db.s9y_config_entry('fetchLimit'))
        if (fetchlimit < 1):
            logging.error("fetchLimit in S9y is invalid!")
            sys.exit(1)

        for t in tags:
            if (t['entryid'] not in self.tags_by_id):
                self.tags_by_id[t['entryid']] = []
            self.tags_by_id[t['entryid']].append(t['tag'])
            if (t['tag'] not in self.tags_by_name):
                self.tags_by_name[t['tag']] = []
            self.tags_by_name[t['tag']].append(t['entryid'])

            tag_name = t['tag']
            tag_name_old = self._serendipity_makeFilename(tag_name)
            tag_url_old = "{owp}plugin/tag/{name}".format(owp = self.config.arguments.oldwebprefix,
                                                          name = tag_name_old)

            tag_name_new = self._sanitize_url_string(tag_name).lower()
            tag_url_new = "{nwp}tags/{name}/".format(nwp = self.config.arguments.webprefix,
                                                          name = tag_name_new)

            if (self.use_tags):
                self._write_rewrite_file(tag_url_old, tag_url_new, '')
            else:
                # tag taxonomy is not used, but the old URLs exist
                # redirect this to the main page
                self._write_rewrite_file(tag_url_old, self.config.arguments.webprefix, '')

            if (t['entryid'] not in self.tags_by_id_new):
                self.tags_by_id_new[t['entryid']] = []
            self.tags_by_id_new[t['entryid']].append(tag_name_new)

            # S9y creates listing pages for all tags in the format:
            # /plugin/tag/<tag>/P<number>.html
            # need to know how many of such pages exist
            number_entries = self.db.number_entries_by_tag(t['tag'])
            number_pages = int(number_entries / fetchlimit) + 1
            for n in range(1, number_pages + 1):
                tag_url_old = "{owp}plugin/tag/{name}/P{n}.html".format(owp = self.config.arguments.oldwebprefix,
                                                                        name = tag_name_old,
                                                                        n = n)
                if (self.use_tags):
                    self._write_rewrite_file(tag_url_old, tag_url_new, '')
                else:
                    # tag taxonomy is not used, but the old URLs exist
                    # redirect this to the main page
                    self._write_rewrite_file(tag_url_old, self.config.arguments.webprefix, '')


    def permalinks(self):
        logging.debug("Reading permalinks")
        permalinks = self.db.permalinks()
        #print(permalinks)
        for p in permalinks:
            if (p['type'] == 'entry'):
                self.permalinks_by_id[p['entry_id']] = p


    def _rewrite_url(self, url, entry):
        new_url = url

        # the URL is relative, starting on where the old blog lives
        # S9y doesn't know the full path
        if (new_url[0:9] == 'archives/'):
            new_url = new_url[9:]

        if (new_url[-5:] == '.html'):
            new_url = new_url[:-5]

        if (self.config.arguments.remove_s9y_id):
            new_url = re.sub(r'^[0-9]+\-', '', new_url)

        if (self.config.arguments.add_date_to_url):
            ts_time, ts_date = self._date_and_time_for_entry(entry['timestamp'])
            new_url = ts_date + '_' + new_url

        # urlize() in Hugo makes all URLs lowercase
        new_url = new_url.lower()

        if (self.config.arguments.use_bundles):
            # post is a directory, and then "index.md" as filename
            new_file = os.path.join('post', new_url, "index.md")
        else:
            # filename is always local to the Hugo directory
            new_file = os.path.join('post', new_url + ".md")

        if (self.config.arguments.webprefix != ''):
            new_url = self.config.arguments.webprefix + "post/" + new_url
        else:
            new_url = "post/" + new_url

        new_url += "/"

        #print(url)
        #print(new_url)

        if (new_url in self.seen_new_urls):
            logging.error("Can't rewrite old URL into new one, found duplicates!")
            logging.error("Old URL: {url}".format(url = url))
            logging.error("New URL: {url}".format(url = new_url))
            logging.error("Consider using the '--add-date-to-url' option")
            sys.exit(1)
        self.seen_new_urls[new_url] = True

        return new_url, new_file


    def _write_rewrite_file(self, old_url, new_url, entry, keep_hashtag_in_new = False):
        if (old_url[0:1] != '/'):
            logging.error("Old URL for redirect must be absolute!")
            logging.error("URL: {u}".format(u = old_url))
            sys.exit(1)
        if (new_url[0:1] != '/'):
            logging.error("New URL for redirect must be absolute!")
            logging.error("URL: {u}".format(u = new_url))
            sys.exit(1)

        if (old_url in self.redirect_links_seen):
            # seen this URL before, don't write another entry'
            return

        if (self.config.arguments.rewritetype == "apache2"):
            old_entry = urllib.parse.quote(old_url)
            new_entry = urllib.parse.quote(new_url)
            if (keep_hashtag_in_new):
                # mainly used for archive links redirecting to the correct year
                new_entry = new_entry.replace('%23', '#', 1)
            with open(self.config.arguments.rewritefile, 'a') as f:
                # all URLs are absolute, this allows placing the redirect
                # file anywhere
                f.write("RedirectMatch 301 {old} {new}\n".format(old = old_entry,
                                                                 new = new_entry))
            logging.debug("Writing redirect: {old} -> {new}".format(old = old_entry,
                                                                    new = new_entry))

        # store entry to avoid writing it again next time
        self.redirect_links_seen[old_url] = new_url


    def _move_image(self, source, target):
        if (os.path.exists(target)):
            logging.debug("Image already exists: {target}".format(target = target))
            return
        targetdir = os.path.dirname(target)
        self.ensure_directory_exists(targetdir)
        logging.debug("Move image: {source} -> {target}".format(source = source, target = target))
        shutil.copyfile(source, target)


    def _rewrite_images(self, body, link, new_link, new_file, new_full_file):
        img = re.findall(r'\!\[(.*?)\]\((.*?)\)', body, re.MULTILINE)
        #print(img)
        for i in img:
            img_comment = i[0]
            img_path = i[1]
            # can only work on local images, not something which is linked from other websites
            # also only works on images with absolute path, however S9y should have
            # added all images with absolute path anyway
            if (img_path[0] == "/"):
                # if the path starts with "/", the full local path can't be calculated
                img_realpath = os.path.realpath(os.path.join(self.config.arguments.imagedir, img_path[1:]))
                if (not os.path.exists(img_realpath)):
                    if (type(self.config.arguments.ignore_picture_errors) is list and link in self.config.arguments.ignore_picture_errors):
                        # picture errors are to be ignored
                        # add a comment to the picture
                        original_text = '![{comment}]({path})'.format(comment = img_comment, path = img_path)
                        if (img_comment == ""):
                            replace_text = '![PICTUREISMISSING]({path})'.format(path = img_path)
                        else:
                            replace_text = '![{comment} - PICTUREISMISSING]({path})'.format(comment = img_comment, path = img_path)
                        body = body.replace(original_text, replace_text)
                    else:
                        # picture errors are a problem, raise it
                        logging.error("Linked image doesn't exist: {img}".format(img = img_path))
                        logging.error("Local image: {img}".format(img = img_realpath))
                        sys.exit(1)
                else:
                    if (self.config.arguments.use_bundles):
                        # Hugo bundles are being used, place all images in the bundle directory as resource
                        new_image_filename = new_full_file.removesuffix('index.md') + os.path.basename(img_realpath)
                        self._move_image(img_realpath, new_image_filename)
                        original_text = '![{comment}]({path})'.format(comment = img_comment, path = img_path)
                        replace_text = '![{comment}]({path})'.format(comment = img_comment, path = os.path.basename(img_realpath))
                        body = body.replace(original_text, replace_text)
                    else:
                        # the image path has the $webprefix already included
                        # needs to be rewritten for old and new webroot
                        # the img_path is relative, need to complete it first
                        # this might pose the problem that the old webprefix appears more than once
                        target_filename = os.path.realpath(os.path.join(self.config.arguments.targetdir, 'static', img_path[1:]))
                        target_filename = target_filename.replace(self.config.arguments.oldwebprefix, self.config.arguments.webprefix)
                        self._move_image(img_realpath, target_filename)
                        original_text = '![{comment}]({path})'.format(comment = img_comment, path = img_path)
                        replace_text = '![{comment}]({path})'.format(comment = img_comment, path = img_path.replace(self.config.arguments.oldwebprefix, self.config.arguments.webprefix))
                        body = body.replace(original_text, replace_text)

        return body


    # some of the comments look like this:
    # ![](/path/to/picture.jpg "This is the comment")
    def _fix_image_comments(self, body, link):
        img = re.findall(r'\!\[(.*?)\]\((.*?)\)', body, re.MULTILINE)
        #print(img)
        for i in img:
            img_comment = i[0]
            img_path = i[1]
            # can only work on local images, not something which is linked from other websites
            if (img_path[0] == "/"):
                img_parts = re.search(r'^(.*?\.[a-zA-Z0-9]+) "(.*)"$', img_path)
                if (img_parts):
                    # now there's a chance that the original comment is not empty
                    if (img_comment == ""):
                        new_comment = "TEXTREPLACED: {text}".format(text = img_parts.group(2))
                    else:
                        new_comment = "{oldtext} - TEXTREPLACED: {text}".format(oldtext = img_comment, text = img_parts.group(2))
                    original_text = '![{comment}]({path})'.format(comment = img_comment, path = img_path)
                    replace_text = '![{comment}]({path})'.format(comment = new_comment, path = img_parts.group(1))
                    #print(original_text)
                    #print(replace_text)
                    body = body.replace(original_text, replace_text)

        return body


    def _fix_unsupported_html(self, body, link, fm):
        unsupported = False

        # <strike> </strike>
        body = body.replace('<strike>', '<del>')
        body = body.replace('</strike>', '</del>')

        # <s> </s> is recognized by the Markdown parser

        # <u> </u> was "underline" in HTML4, and has a different meaning in HTML5
        #  it is ignored by the parser
        if ('<u>' in body):
            unsupported = True

        return body, unsupported


    def _fix_quoted_html(self, fm):
        fm_new = fm
        fm_new = fm_new.replace('\\\\*', '*')
        fm_new = fm_new.replace('\\*', '*')

        changed = False
        if (fm_new != fm):
            changed = True

        return fm_new, changed


    def _rewrite_html(self, body, link, fm, new_link, new_file, new_full_file):
        body, unsupported = self._fix_unsupported_html(body, link, fm)
        parsed_body = body

        md = markdownify.markdownify(body)
        #md = markdown.replace('```\n\n', '```\n')
        #md = re.sub(r"```[\n]+", "```", md, flags = re.MULTILINE)
        md = re.sub(r'\n\s*\n', '\n\n', md)
        #print(md)
        md = self._fix_image_comments(md, link)
        md = self._rewrite_images(md, link, new_link, new_file, new_full_file)
        md, quotes_changed = self._fix_quoted_html(md)

        md = "{md}\n".format(md = md.strip())

        # Hugo doesn't like when these tags are not escaped
        md = md.replace('{{', '\\{\\{')
        md = md.replace('}}', '\\}\\}')

        return md, parsed_body, unsupported, quotes_changed


    def _date_and_time_for_entry(self, ts):
        # the S9y database only has a timestamp in seconds
        # and it's in UTC time

        if (self.config.arguments.use_utc):
            orig_time = datetime.utcfromtimestamp(ts)
            orig_tz = "+0000"
        else:
            orig_time = datetime.fromtimestamp(ts, gettz())
            orig_tz = orig_time.strftime('%z')

        td = orig_time.strftime('%Y-%m-%d')
        ts = orig_time.strftime('%Y-%m-%dT%H:%M:%S')
        # in theory Python can produce strange formats for the TZ
        tz_match = re.match(r'^([\+\-])(\d\d)(\d\d)$', orig_tz)
        if (not tz_match):
            logging.error("Error extracting TZ information from timestamp!")
            logging.error("TS: {ts}".format(ts = entry['timestamp']))
            logging.error("TZ: {tz}".format(tz = tz))
        ts += "{prefix}{hours}:{minutes}".format(prefix = tz_match.group(1), hours = tz_match.group(2), minutes = tz_match.group(3))

        return ts, td


    def _generate_frontmatter(self, fm, id, entry, body):
        ts_time, ts_date = self._date_and_time_for_entry(entry['timestamp'])
        fm['title'] = entry['title']
        # S9y only knows one author, Hugo allows multiple authors
        fm['authors'] = self.authors_by_id[entry['authorid']]['username']
        if (entry['isdraft'] is False):
            fm['draft'] = False
        else:
            fm['draft'] = True
        fm['date'] = ts_time
        fm['s9yID'] = id
        fm['s9yTS'] = entry['timestamp']

        # handle categories
        if (fm.get('categories') == None):
            fm['categories'] = []
        if (id in self.entry_categories_by_entry):
            for e in self.entry_categories_by_entry[id]:
                # if no category is assigned, S9y uses '0'
                if (e == 0):
                    continue
                if (e not in self.categories_by_id):
                    # mostly affects the "/" category
                    fm['CATEGORIESSKIPPED'] = int(e)
                    continue
                # if the file is updated (instead of newly generated), the categories
                # might already be in there
                c_name = self._sanitize_url_string(self.categories_by_id[e]['category_name'])
                if (c_name.lower() not in fm['categories']):
                    fm['categories'].append(c_name.lower())
        if (len(fm['categories']) == 0):
            # otherwise this will show up as [] in the Frontmatter output
            del(fm['categories'])

        # handle tags
        if (fm.get('tags') == None):
            fm['tags'] = []
        if (id in self.tags_by_id):
            for t in self.tags_by_id[id]:
                # if the file is updated (instead of newly generated), the tags
                # might already be in there
                t_name = self._sanitize_url_string(t)
                if (t_name.lower() not in fm['tags']):
                    fm['tags'].append(t_name.lower())
        if (len(fm['tags']) == 0):
            # otherwise this will show up as [] in the Frontmatter output
            del(fm['tags'])

        fm.content = body

        return fm


    # this extracts the Hugo configuration for the targetdir
    # and stores it in the class
    def _get_hugo_config(self):
        logging.debug("Extracting Hugo configuration")
        p = subprocess.Popen([self.config.arguments.hugo_bin, 'config'],
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE,
                             universal_newlines = True,
                             cwd = self.config.arguments.targetdir)
        stdout, stderr = p.communicate()

        if (p.returncode != 0):
            logging.error("Something went wrong extracting the Hugo configuration")
            logging.error("RC: {rc}".format(rc = p.returncode))
            logging.error("stdout:\n{s}".format(s = stdout))
            logging.error("stderr:\n{s}".format(s = stderr))
            sys.exit(1)

        for l in stdout.splitlines():
            k = l.split(' = ', 1)[0]
            v = l.split(' = ', 1)[1]
            if (v.startswith('map[') and v.endswith(']')):
                # Note: this only extracts the first level of maps
                #       fields like 'params' have multiple levels
                self.parsed_hugo_config[k] = v[4:-1]
            else:
                self.parsed_hugo_config[k] = v.strip('"')

        taxonomies = self.parsed_hugo_config['taxonomies']
        # set taxonomy flags which are relevant for migration
        if ('category:categories' in taxonomies):
            self.use_categories = True
        if ('tag:tags' in taxonomies):
            self.use_tags = True
        if ('author:authors' in taxonomies):
            self.use_authors = True


    def _generate_hugo_file(self, new_file, new_full_file):
        logging.debug("Creating Hugo posting: {f}".format(f = new_file))
        p = subprocess.Popen([self.config.arguments.hugo_bin, 'new', new_file],
                             stdout = subprocess.PIPE,
                             stderr = subprocess.PIPE,
                             universal_newlines = True,
                             cwd = self.config.arguments.targetdir)
        stdout, stderr = p.communicate()

        if (p.returncode != 0):
            logging.error("Something went wrong creating the Hugo file")
            logging.error("RC: {rc}".format(rc = p.returncode))
            logging.error("stdout:\n{s}".format(s = stdout))
            logging.error("stderr:\n{s}".format(s = stderr))
            sys.exit(1)

        # verify that the created name is indeed what we
        # expect (second function parameter)
        file_match = re.match(r'^Content "(.+)" created$', stdout)
        if (not file_match):
            logging.error("Can't find expected string in stdout!")
            logging.error("stdout:\n{s}".format(s = stdout))
            logging.error("stderr:\n{s}".format(s = stderr))
            sys.exit(1)

        if (file_match.group(1) != new_full_file):
            logging.error("Expected file does not match created file!")
            logging.error("Expected: {f}".format(f = new_full_file))
            logging.error(" Created: {f}".format(f = file_match.group(1)))
            sys.exit(1)


    # main function, going over all blog postings
    def entries(self):
        found_replacements = False
        number_migrated = 0
        number_ignored = 0
        number_marked = 0
        unsupported_tags = 0
        quotes_changed = 0

        logging.debug("Reading entries")
        entries = self.db.entries()
        #print(entries)
        logging.debug("Have {c} blog entries".format(c = len(entries)))
        for e in entries:
            #print(e)
            link = self.permalinks_by_id[e['id']][0]
            if (type(self.config.arguments.ignore_post) is list and link in self.config.arguments.ignore_post):
                logging.info("Ignoring post: {link}".format(link = link))
                number_ignored += 1
                continue
            # DEBUG: uncomment and add a link from the S9y blog
            #if (link != ""):
            #    continue
            logging.debug("migrating posting: {link}".format(link = link))
            # also handles Hugo Bundles
            new_link, new_file = self._rewrite_url(link, e)
            new_full_file = self.hugo_path('content', new_file)
            if (not self.file_exists(new_full_file)):
                # use the Hugo binary to create this file
                # this has the advantage that the full template can be used
                # and we later fill in the details
                # otherwise we have to fill in the file from scratch, and this
                # might be plenty of migration work
                self._generate_hugo_file(new_file, new_full_file)
            old_url = link
            if (old_url[0:1] != '/'):
                # complete the old URL with webroot
                # required to write a full path into the redirect file
                old_url = self.config.arguments.oldwebprefix + old_url
            self._write_rewrite_file(old_url, new_link, e)

            # get the Frontmatter from the content file
            fm = frontmatter.load(new_full_file)

            body = e['body'] + "\n\n" + e['extended']
            #print(body)
            original_body = body
            body, parsed_body, unsupported, quotes_changed_here = self._rewrite_html(body, link, fm, new_link, new_file, new_full_file)
            if (unsupported):
                unsupported_tags += 1
            if (quotes_changed_here):
                quotes_changed += 1
            if (self.config.arguments.write_html):
                html_filename = new_full_file[:-3] + ".html"
                soup = BeautifulSoup(parsed_body, 'html.parser')
                with open(html_filename, 'w') as html_fh:
                    html_fh.write(original_body)
                    html_fh.write("\n\n\n\n\n\n")
                    html_fh.write(parsed_body)
                    html_fh.write("\n\n\n\n\n\n")
                    html_fh.write(soup.prettify())

            # FIXME: comments

            fm = self._generate_frontmatter(fm, e['id'], e, body)

            if ('TEXTREPLACED' in body or 'PICTUREISMISSING' in body):
                found_replacements = True
                number_marked += 1
                if ('TEXTREPLACED' in body):
                    fm['TextReplaced'] = True
                if ('PICTUREISMISSING' in body):
                    fm['PictureMissing'] = True
            if (unsupported):
                fm['UnsupportedTags'] = True
            if (quotes_changed_here):
                fm['QuotesChanged'] = True

            fm['OriginalLink'] = link

            fh = io.open(new_full_file, 'w', encoding = 'utf8')
            fh.write(frontmatter.dumps(fm))
            fh.write("\n")
            fh.close()

            number_migrated += 1

        if (found_replacements):
            logging.info("Found migration markers ...")
            logging.info("Check for 'TEXTREPLACED', 'PICTUREISMISSING' and 'CATEGORIESSKIPPED' in migrated files, also see README")
        if (unsupported_tags > 0):
            logging.info("Found markers for unsupported HTML4 tags ...")
            logging.info("Check for 'UnsupportedTags' in migrated files")
            if (not self.config.arguments.write_html):
                logging.info("And consider using --write-html for writing the S9y source to files")

        logging.info("{n} postings migrated".format(n = number_migrated))
        logging.info("{n} postings ignored".format(n = number_ignored))
        logging.info("{n} postings with unsupported tags".format(n = unsupported_tags))
        logging.info("{n} postings with changed quotes".format(n = quotes_changed))
        logging.info("{n} postings need additional work".format(n = number_marked))


    def archive(self):
        oldest_entry = False

        # find oldest entry
        entries = self.db.entries()
        for e in entries:
            if (oldest_entry is False):
                oldest_entry = e
            if (e['timestamp'] < oldest_entry['timestamp']):
                oldest_entry = e

        if (oldest_entry is False):
            # nothing to do here
            return

        oldest_time, oldest_date = self._date_and_time_for_entry(oldest_entry['timestamp'])
        oldest_year = oldest_date[0:4]
        if (int(oldest_year) < 2000):
            # Serendipity project was started around 2002
            logging.error("Serious concerns about the date of the oldest entry in the database!")
            logging.error("Date is: {date}".format(date = oldest_date))
            sys.exit(1)

        # S9y has an /archive link
        old_url = "{owp}archive".format(owp = self.config.arguments.oldwebprefix)
        self._write_rewrite_file(old_url, self.config.arguments.archive_link, '')

        this_year = datetime.now().year
        # also generate links for every year and month the blog is active
        for year in range(int(oldest_year), int(this_year) + 1):
            if (self.config.arguments.add_year_link_to_archive):
                redirect_link = "{al}#{year}".format(al = self.config.arguments.archive_link,
                                                     year = year)
            else:
                redirect_link = self.config.arguments.archive_link
            for month in range(1, 12 + 1):
                old_url = "{owp}archives/{year}/{month:02d}.html".format(owp = self.config.arguments.oldwebprefix,
                                                                         year = year, month = month)
                self._write_rewrite_file(old_url, redirect_link, '', keep_hashtag_in_new = True)
                old_url = "{owp}archives/{year}/{month:02d}/summary.html".format(owp = self.config.arguments.oldwebprefix,
                                                                                 year = year, month = month)
                self._write_rewrite_file(old_url, redirect_link, '', keep_hashtag_in_new = True)


# end Migration class
#######################################################################





def main():
    config = Config()
    config.parse_parameters()

    database = Database(config)

    migration = Migration(config, database)
    migration.archive()
    migration.authors()
    migration.categories()
    migration.entry_categories()
    migration.tags()
    migration.permalinks()
    migration.entries()


if __name__ == '__main__':
    main()
