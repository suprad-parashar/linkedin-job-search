#Selenium Imports
from selenium import webdriver
import selenium
import selenium.common
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

#Other Imports
from dotenv import load_dotenv
import pandas as pd
import click
from tqdm import tqdm
import google.generativeai as genai
import html2text

#Python Imports
import json
import shutil
import time
import os
from datetime import datetime

# Load Environment Variables
# Configure the environment variables in a .env file.
# Environment Variables:
# LINKEDIN_EMAIL - Your LinkedIn Email
# LINKEDIN_PASSWORD - Your LinkedIn Password
# API_KEY - Your Gemini AI API Key
load_dotenv()

SEARCH_QUERY = "software engineer"
LOCATION = "USA"
TIME = "24H"
EASY_APPLY = False

CHROME_DRIVER_PATH = "/Users/supradparashar/chromedriver"
TIMEOUT = 0.5
SLEEP_TIME = 0.5

EMAIL = os.getenv("LINKEDIN_EMAIL") or ""
PASSWORD = os.getenv("LINKEDIN_PASSWORD") or ""
API_KEY = os.getenv("API_KEY")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def wait(multiplier=1):
    time.sleep(SLEEP_TIME * multiplier)

def scroll_down(driver: webdriver.Chrome):
    cur = 0
    height = driver.execute_script("return document.body.scrollHeight")
    while cur < height:
        cur += 500
        driver.execute_script(f"window.scrollTo(0, {cur});")
        wait()
        height = driver.execute_script("return document.body.scrollHeight")

def login(driver: webdriver.Chrome):
    driver.get("https://www.linkedin.com/login")
    wait()
    WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="username"]'))).send_keys(EMAIL)
    WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="password"]'))).send_keys(PASSWORD)
    try:
        WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="organic-div"]/form/div[4]/button'))).click()
    except:
        WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="organic-div"]/form/div[3]/button'))).click()
    wait(2)
    while driver.current_url != "https://www.linkedin.com/feed/":
        pass

def get_text_from_element(element):
    text = ""
    queue = [element]
    while queue:
        cur = queue.pop(0)
        # print(cur.get_attribute("innerHTML"))
        text += cur.get_attribute("innerText")
        children = cur.find_elements(By.XPATH, './*')
        queue.extend(children)
    return text

def get_time_param(timeline):
    # global TIME
    if timeline == "24H":
        return "&f_TPR=r86400"
    if timeline == "7D" or timeline == "1W":
        return "&f_TPR=r604800"
    if timeline == "1M":
        return "&f_TPR=r2592000"
    return ""

def get_geo_id(location):
    if location.lower() == "usa" or location.lower() == "united states" or location.lower() == "america" or location.lower() == "us" or location.lower() == "united states of america":
        return "103644278"
    if location.lower() == "india" or location.lower() == "in" or location.lower() == "ind":
        return "102713980"
    if location.lower() == "germany" or location.lower() == "de" or location.lower() == "ger" or location.lower() == "deutschland" or location.lower() == "deu":
        return "101282230"
    if location.lower() == "singapore" or location.lower() == "sg" or location.lower() == "sing" or location.lower() == "sin":
        return "102454443"
    if location.lower() == "uae" or location.lower() == "united arab emirates" or location.lower() == "dubai":
        return "106204383"
    return "103644278"

def easy_apply(job_link, driver):
    driver.get(job_link)
    apply_button = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '/html/body/div[6]/div[3]/div[2]/div/div/main/div[2]/div[1]/div/div[1]/div/div/div/div[5]/div/div/div/button')))
    apply_button.click()
    wait(2)

def get_jobs_specific(driver: webdriver.Chrome, search_query, location, timeline, easy_apply, page_count = 3, suffix=""):
    global SEARCH_QUERY, LOCATION, TIME, EASY_APPLY
    text_maker = html2text.HTML2Text()
    text_maker.ignore_links = True
    text_maker.ignore_images = True
    text_maker.wrap_links = True
    text_maker.wrap_lists = True
    completed_list = []
    print("Starting job search...")
    for page in range(page_count):
        main_link = f"https://www.linkedin.com/jobs/search/?{"f_AL=true" if easy_apply else ""}{get_time_param(timeline)}&geoId={get_geo_id(location)}&keywords={search_query.replace(" ", "%20")}&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true&spellCorrectionEnabled=true&start={25 * page}"
        driver.get(main_link)
        wait(5)
        jobs_ul = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/div/div[2]/div[1]/div/ul')))
        jobs = jobs_ul.find_elements(By.XPATH, './li')
        i = 0
        while i < len(jobs):
            try:
                jobs[i].click()
                wait(3)
                job_a = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/div/div[2]/div[2]/div/div[2]/div/div/div[1]/div/div[1]/div/div[1]/div/div[2]/div/h1/a')))
                job_link = job_a.get_attribute("href")
                job_heading = job_a.get_attribute("innerText")
                job_heading = job_heading.replace(",", "")
                article = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/div/div[2]/div[2]/div/div[2]/div/div/div[1]/div/div[4]/article')))
                jd = text_maker.handle(article.get_attribute("innerHTML"))
                response = model.generate_content(f"""
                    The following is the job description. Parse it and provide the following details in a JSON format.
                    Return a JSON containing the company's name under the key 'company',
                    minimum years of experience as 'min_exp', maximum years of experience as 'max_exp'.
                    Use 'N/A' if the min and max exp is not available.
                    Add a key 'age_match' which is True if the job is suitable for a candidate with 2 years of experience. If the experience needed is not mentioned, set it to True anyway. Always set it to True unless the job description explicitly mentions the experience needed and it is not in the range of 1.5 to 2 years.
                    Also categorise the job into one of the following buckets after reading the job description - 
                        [Java, Python, Web Development, API Development, Rust, Full Stack, Mobile Development, Microservices, 
                        API Development, Healthcare, Generative AI, Databases, Data Engineering, DevOps, Finance,
                        Cloud Development, SDE, Big Data, Machine Learning].
                    Provide an overall category called 'overall' which is the most relevant category from the above list. To help you categorise, you can use the following descriptions for each category:
                        Java - Anything that is predominantly Java related. This includes Java, Spring, J2EE, etc.
                        Python - Anything that is predominantly Python related. This includes Python, Django, Flask, etc.
                        Web Development - Anything that is predominantly web development related. This includes HTML, CSS, JavaScript, etc.
                        API Development - Anything that is predominantly API development related. This includes REST, SOAP, etc.
                        Rust - Anything that is predominantly Rust related.
                        Full Stack - Anything that is mostly backend with some amount of frontend development.
                        Mobile Development - Anything that is predominantly Mobile Development related. This includes Android, iOS, etc.
                        Microservices - Anything that is predominantly Microservices related. This includes Kubernetes, Docker, etc.
                        Healthcare - Anything that is predominantly Healthcare related. This includes HL7, FHIR, etc.
                        Generative AI - Anything that is predominantly Generative AI related. This includes GANs, Transformers, etc.
                        Databases - Anything that is predominantly Database related. This includes SQL, NoSQL, etc.
                        Data Engineering - Anything that is predominantly Data Engineering related. This includes ETL, Data Pipelines, etc.
                        DevOps - Anything that is predominantly DevOps related. This includes Kubernetes, Docker, etc.
                        Finance - Anything that is predominantly Finance related. This includes Trading, Risk Management, etc.
                        Cloud Development - Anything that is predominantly Cloud Development related. This includes AWS, Azure, etc.
                        SDE - Anything that is predominantly Software Development related. This includes Software Development, etc.
                        Big Data - Anything that is predominantly Big Data related. This includes Hadoop, Spark, etc.
                        Machine Learning - Anything that is predominantly Machine Learning related. This includes ML, DL, etc.
                    Give a primary category and secondary category for the job categories. Use the keys 'primary' and 'secondary'.
                    Both primary and secondary needs to be from only the above mentioned categories.
                    Provide details on whether the job requires US citizenship or not. Use the key 'citizenship_required'. Default is False.
                    Similarly provide details on whether the job requires a security clearance or not. Use the key 'security_clearance_required'. Default is False.
                    Similarly provide details on whether the job provides visa sponsorship or not. Use the key 'visa_sponsorship'. Default is True.
                    Generate only the JSON and nothing else.\n\n{jd}"""
                ).text
                response = response[8:]
                response = response[:-4]
                job_data = json.loads(response)
                job_data["link"] = job_link
                job_data["title"] = job_heading
                with open(f"jobs_{get_geo_id(location)}_{timeline}_{easy_apply}_{search_query}{"" if suffix == "" else "_" + suffix}.csv", "a") as f:
                    f.write(f"{job_data['title']},{job_data['company'].replace(",", "")},{job_data['min_exp']},{job_data['max_exp']},{job_data['age_match']},{job_data["overall"]},{job_data['primary']},{job_data['secondary']},{job_data['citizenship_required']},{job_data['security_clearance_required']},{job_data['visa_sponsorship']},{job_data['link']}\n")
                print(f"Page: {page + 1}, Job: {i + 1} completed.")
                i += 1
            except selenium.common.exceptions.TimeoutException as e:
                # print(e)
                print("Timeout exception.")
                jobs[i].click()
                wait(5)
                try:
                    job_a = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/div/div[2]/div[2]/div/div[2]/div/div[1]/div/div[1]/div/div[1]/div/div[2]/div/h1/a')))
                    job_link = job_a.get_attribute("href")
                    print(f"Link of Job - {job_link}")
                    with open("error_links.txt", "a") as f:
                        f.write(f"{job_link}\n")
                except:
                    print("Skipping...")
                    continue
                i += 1
            except Exception as e:
                print(e)
                print("RPM exceeded. Waiting for 60 seconds...")
                time.sleep(60)
                print("Resuming...")
                continue

def specific_pipeline(driver: webdriver.Chrome, search_query, location, timeline, easy_apply, page_count = 3, suffix=""):
    login(driver)
    print("Logged in successfully...")
    get_jobs_specific(driver, search_query, location, timeline, easy_apply, page_count, suffix)
    driver.close()

def merge_files(location, search_query, easy_apply, should_delete=True):
    columns = ["title", "company", "min_exp", "max_exp", "age_match", "overall", "primary", "secondary", "citizenship_required", "security_clearance_required", "visa_sponsorship", "link"]
    timelines = ["24H", "7D", "1M"]
    # frames = [pd.read_csv(f"jobs_{get_geo_id(location)}_{timeline}_{easy_apply}_{search_query}_DAILYROUTINE.csv", header=None, names=columns) for timeline in timelines]
    df = pd.DataFrame(columns=columns)
    for timeline in timelines:
        frame = pd.read_csv(f"jobs_{get_geo_id(location)}_{timeline}_{easy_apply}_{search_query}_DAILYROUTINE.csv", header=None, names=columns)
        df = pd.concat([df, frame])
    df.to_csv(f"jobs_DAILY_{datetime.strftime(datetime.now(), '%d-%m-%Y')}_{get_geo_id(location)}_{easy_apply}_{search_query}.csv", index=False)
    if not should_delete:
        return
    for timeline in timelines:
        os.remove(f"jobs_{get_geo_id(location)}_{timeline}_{easy_apply}_{search_query}_DAILYROUTINE.csv")

def daily_pipeline(driver: webdriver.Chrome, search_query, location, easy_apply):
    login(driver)
    print("Logged in successfully...")
    timelines = [("24H", 2), ("7D", 1), ("1M", 1)]
    for timeline, page_count in timelines:
        get_jobs_specific(driver, search_query, location, timeline, easy_apply, page_count, "DAILYROUTINE")
    merge_files(location, search_query, easy_apply)
    shutil.copyfile(f"jobs_DAILY_{datetime.strftime(datetime.now(), '%d-%m-%Y')}_{get_geo_id(location)}_{easy_apply}_{search_query}.csv", f"/Users/supradparashar/Documents/Suprad/jobs_DAILY_{datetime.strftime(datetime.now(), '%d-%m-%Y')}_{get_geo_id(location)}_{easy_apply}_{search_query}_DAILYROUTINE.csv")

@click.command()
@click.option('--search_query', default=SEARCH_QUERY, help='Search query for the job')
@click.option('--location', default=LOCATION, help='Location for the job')
@click.option('--easy_apply', default=EASY_APPLY, help='Easy apply for the job')
def start(search_query, location, easy_apply):
    driver = webdriver.Chrome(service=Service(CHROME_DRIVER_PATH))
    driver.maximize_window()
    daily_pipeline(driver, search_query, location, easy_apply)
    driver.close()

if __name__ == "__main__":
    start()