import os
import re
import urllib
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from bs4 import BeautifulSoup as soup
import time
import pandas as pd
import random
from db import DB
import sys


URL_HOME = 'https://www.list.am/en'
db = DB()


def page_soup(url: str):
    """Parameter `url`: web address of page to parse.
    In case of failure prints error, otherwise returns `BeautifulSoup` object: parsed html document (str),
    """
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        webpage = urlopen(req).read().decode('utf-8')
        pg_soup = soup(webpage, "html.parser")
    except urllib.error.HTTPError as errh:
        print(f'Error during fetching of website:')
        return errh
    except urllib.error.URLError as erru:
        print(f'Error during fetching of website:')
        return erru
    else:
        return pg_soup


def get_categories_paths():
    """Returns all categories' names and paths in a dictionary.
    e.g. {'Apartments for sale': '/category/60', 'Houses for rent: '/category/63', ...} """
    conn, cur = db.conn, db.cur
    if db.check_table('property_type') == True:
        select_cat = cur.execute('''SELECT name, q_string
                                    FROM property_type;''')
        cat_paths = cur.fetchall()
        if len(cat_paths) > 0:
            return cat_paths

    url = 'https://www.list.am/en/category/54'  # arbitrary category url to fetch all categories paths
    pg_soup = page_soup(url)
    section_cat = pg_soup.select('div.s')
    categories_dict = dict()
    for cat in section_cat:
        tmp = cat.next.lower().strip()
        if tmp == 'for rent':
            for elem in cat.select('a'):
                categories_dict[elem.text + ' for rent'] = elem['href']
        elif tmp == 'for sale':
            for elem in cat.select('a'):
                categories_dict[elem.text + ' for sale'] = elem['href']
        elif tmp == 'new construction':
            for elem in cat.select('a'):
                categories_dict[elem.text + ' new construction'] = elem['href']
    create_table = ('''CREATE TABLE IF NOT EXISTS property_type
                                              (id SERIAL PRIMARY KEY,
                                              name VARCHAR(255),
                                              q_string VARCHAR(16) UNIQUE)''')
    cur.execute(create_table)
    insert_to_table = '''INSERT INTO property_type (name, q_string)
                         VALUES (%s, %s)
                         ON CONFLICT (q_string) DO NOTHING;
                       '''
    for key, value in categories_dict.items():
        cur.execute(insert_to_table, (key, value))
    conn.commit()
    return get_categories_paths


def get_regions():
    """
    Returns all region names and query string in a dictionary.
    e.g. {'Yerevan': '?n=1', 'Armavir': '?n=23', ...}
    """
    url = 'https://www.list.am/en/category/'  # url to fetch all region paths
    pg_soup = page_soup(url)

    # select all `divs` that contain region names
    data_searchname = pg_soup.find_all('div', {'class': 'i', 'data-name': re.compile('^[A-z]')})  # data-name - to
    # filter out city names
    loc_dict = dict()
    for data in data_searchname[1:len(data_searchname) - 1]:  # slicing to exclude option 'All'
        if data['data-name'] not in loc_dict:
            loc_dict[data['data-name']] = '?n=' + data['data-value']
    return loc_dict


def get_ad_links(url: str, key_cat: str, key_loc: str):
    a_tags = []
    page_num = 1
    while True:  # loop through each page of pagination
        pg_soup = page_soup(url)
        # append list with `a` tags containing path to ad, e.g /en/item/16954298
        a_tags.extend(pg_soup.select('div.gl a'))
        # locate the `Next` button
        next_page_element = pg_soup.find('a', text='Next >')
        if next_page_element:
            next_page_url = next_page_element.get('href')
            url = URL_HOME + next_page_url
        else:
            break
        # time.sleep(random.randint(2, 5))
        page_num += 1
        sys.stdout.write(f"\r{key_cat} category for {key_loc} region: page %i" % page_num)
        sys.stdout.flush()

    try:
        pass
    except:
        links = dict()

    for a in a_tags:
        full_url = 'https://list.am' + a['href']
        conn, cur = db.connect()
        cur.execute('''SELECT links
                       FROM tables
                       WHERE table_name=%s)''', (mytable,))
        if full in urls_data.tolist():
            continue
        if full_url not in links.values():
            links.update({len(links): full_url})

    print('Done')
    return links.values()


if __name__ == '__main__':
    # conn, cur = db.connect()
    # cur.execute('''SELECT name, q_string
    #                FROM property_type;''')
    category_paths = get_categories_paths()
    # cur.execute('''SELECT name, q_string
    #                FROM regions;''')
    # regions = cur.fetchall()
    # For each category pages (Apartments, Houses, Lands, etc.) go over every region (Yerevan, Armavir, Ararat, etc.)
    for cat, cat_path in category_paths:
        for reg, reg_path in regions:
            url = URL_HOME + cat_path + reg_path
            get_ad_links(url, cat, reg)

