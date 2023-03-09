from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from time import sleep

import sqlite3
from sqlite3 import Error

import sys

from pathlib import Path

__author__ = "matthew smith"
__copyright__ = " Copyright 2023, matthew smith"
__credits__ = ["Josh McVay"]
__version__ = "0.95"
__maintainer__ = "matthew smith"
__email__ = "matthieus.smith@gmail.com"
__status__ = "Alpha"

def populate_links(driver, master_link):
    """"
    Retrieve all the links on a page and adds them to the master_link list
    """
    links = driver.find_elements(By.LINK_TEXT,'View')
    for each in links:
        master_link.append(each.get_attribute('href'))
    return master_link


def make_links(driver, master_link):
    """
    Step through the pages, retrieving all the links 
    """
    while True:
        #get the links on the page
        print('Getting links...')
        populate_links(driver, master_link)
        #get the next page button, and retrieve the next page
        #if there isn't a forward button, we've reached the end
        try:
            print('Moving to the next page...')
            button = driver.find_element(By.CLASS_NAME,'fa-forward')
            button.click()
        except:
            return master_link


def read_linkfile(filename):
    """
    Open the file and read each line. Return the results as a list
    """
    with open(filename, 'r') as linkfile:
        read_links = [] #is it pronounced read or read?
        for line in linkfile: read_links.append(line.strip('\n')) #clean the newline character
    return read_links

def write_linkfile(filename, read_links):
    """
    Store the full link list for later reference.
    """
    with open(filename, 'w') as linkfile:
        for link in read_links: linkfile.write(f'{link} \n')

def scrape_links(driver, read_links, outfile):
    """
    Scrape the data from each page and write the contents to a csv file
    """
    for link in read_links:
        driver.get(link)
        delay = 3
        sleep(3) #delay until the page has been populated
        myElem = WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.CLASS_NAME,'row')))
        #pull the data, write it to the csv
        data = driver.find_elements(By.CSS_SELECTOR,'.col-md-8')
        clean_data = []
        for each in data:
            innerHTML = each.get_attribute('innerHTML').strip()
            for char in ['\n','\r']:
                innerHTML = innerHTML.replace(char,'')
            clean_data.append(f'"{innerHTML}"')

        #now we need to attempt to order the data
        for datum in clean_data:
        #if the county field is numeric, we know it's actually the zip code, and need to insert a blank field
            if clean_data.index(datum) == 5: 
                print(datum.replace('-',''))
                if datum.replace('-','').replace('"','').isnumeric():
                    clean_data.insert(clean_data.index(datum),'""')
        #zip codes will either be 5 or 9 numerals. If there's 10+ chars, it's a phone number
            if clean_data.index(datum) == 6:
                print(len(datum.replace('-','').replace('"','')))
                if len(datum.replace('-','').replace('"','')) >= 10:
                    clean_data.insert(clean_data.index(datum),'""')
            #telephone numbers will never contain the @ symbol
            if clean_data.index(datum) == 7:
                print(datum)
                if '@' in datum:
                    clean_data.insert(clean_data.index(datum),'""')
            #likewise, emails will always contain the @ symbol
            if clean_data.index(datum) == 8:
                print(datum)
                if '@' not in datum:
                    clean_data.insert(clean_data.index(datum),'""')

        #add the url for reference
        clean_data.append(f'"{link}"')
        print(','.join(clean_data))
        outfile.write(','.join(clean_data) + '\n')

def create_connection(db_file):
    """ create the connection to a database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(sqlite3.version)
    except Error as e:
        print(e)
    return conn

def create_table(conn):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    sql_create_mfin_table = """CREATE TABLE IF NOT EXISTS scraped (
                            dba text PRIMARY KEY,
                            lic_type text,
                            lic_exp text,
                            street text,
                            city text,
                            country text,
                            zip text,
                            phone_num text,
                            email text,
                            hours text
                            );"""
    try:
        cur = conn.cursor()
        cur.execute(sql_create_mfin_table)
    except Error as e:
        print(e)

def create_entry(conn, entry):
    """
    Create a new task
    :param conn:
    :param task:
    :return:
    """
    sql = ''' INSERT INTO scraped('dba','lic_type','lic_exp','street','city','county','zip','phone_num','email','hours')
              VALUES(?,?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, issue)
    conn.commit()
    return cur.lastrowid

if __name__ == "__main__":
    #initialize the window
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    #get the target page
    target = 'Grower'
    linkfile = ''
    try:
        target = sys.argv[1]
        linkfile = sys.argv[2]
    except:
        pass
    #check to see if we are targeting a linkfile:
    path = Path(linkfile)
    if path.is_file():
        read_links = read_linkfile(linkfile)
    #otherwise, build a new one
    else:
        driver.get(f'https://omma.us.thentiacloud.net/webs/omma/register/#/business/search/all/{target}')
        print('Loading page...')
        sleep(20)
        read_links = make_links(driver, master_link)
        write_linkfile('linkfile.txt', read_links)
    with open('omma_web_scrape.csv', 'w') as outfile:
        outfile.write('DBA,License Type,License Expiration,Street Address,City,County,ZIP Code,Telephone Number,E-mail,Hours of Operation,URL \n')
        scrape_links(driver, read_links, outfile)