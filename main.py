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
from sentence_transformers import SentenceTransformer

#Python Imports
import json
import shutil
import time
import os
from uuid import uuid4
from datetime import datetime

# Load Environment Variables
# Configure the environment variables in a .env file.
# Environment Variables:
#   LINKEDIN_EMAIL - Your LinkedIn Email
#   LINKEDIN_PASSWORD - Your LinkedIn Password
#   API_KEY - Your Gemini AI API Key
#   CHROME_DRIVER_PATH - Path to the Chrome Driver
#   GEMINI_MODEL_ID - The Model ID for the Gemini AI API
load_dotenv()
EMAIL = os.getenv("LINKEDIN_EMAIL")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")
API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL_ID")
CHROME_DRIVER_PATH = os.getenv("CHROME_DRIVER_PATH")

# Set up the Sentence Transformer Model
sbert_model = SentenceTransformer('all-MiniLM-L6-v2')

# Constants
SEARCH_QUERY = "software engineer"
LOCATION = "USA"
TIME = "24H"
EASY_APPLY = False

# Constants
TIMEOUT = 0.5
SLEEP_TIME = 0.5
WAIT_TIMEOUT = 10

# Configure the Gemini AI API
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

#Function to calculate the cosine similarity between the job description and the resume.
def calculate_similarity(job_description, resume):
    job_embeddings = sbert_model.encode(job_description)
    resume_embeddings = sbert_model.encode(resume)
    return sbert_model.similarity(job_embeddings, resume_embeddings).item() * 100

# Function to login to LinkedIn. In case of two-factor authentication, you will need to manually fill in the captcha.
def login(driver: webdriver.Chrome):
    print("[INFO]\tLogging in to LinkedIn.")
    driver.get("https://www.linkedin.com/login")
    # time.sleep(SLEEP_TIME)
    driver.implicitly_wait(WAIT_TIMEOUT)
    WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="username"]'))).send_keys(EMAIL)
    WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="password"]'))).send_keys(PASSWORD)
    try:
        WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="organic-div"]/form/div[4]/button'))).click()
    except:
        WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="organic-div"]/form/div[3]/button'))).click()
    # time.sleep(SLEEP_TIME * 2)
    driver.implicitly_wait(WAIT_TIMEOUT)
    if driver.current_url != "https://www.linkedin.com/feed/":
        print("[WARNING]\tManual Intervention Needed.")
    while driver.current_url != "https://www.linkedin.com/feed/":
        pass
    print("[INFO]\tLogged in successfully.")

# Function to map the timeline to the URL parameter.
def get_time_param(timeline):
    # global TIME
    if timeline == "24H":
        return "&f_TPR=r86400"
    if timeline == "7D" or timeline == "1W":
        return "&f_TPR=r604800"
    if timeline == "1M":
        return "&f_TPR=r2592000"
    return ""

# Function to map the location to the geo ID.
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

def is_job_suitable(job_data, max_min_exp = 3, citizenship_required = False, security_clearance_required = False, visa_sponsorship = True):
    if not (job_data["min_exp"] == "N/A" or job_data["min_exp"] == "" or job_data["min_exp"] == None or int(job_data["min_exp"]) <= max_min_exp):
        return False
    if job_data["citizenship_required"]:
        return False
    if job_data["security_clearance_required"]:
        return False
    if not job_data["visa_sponsorship"]:
        return False
    return True

# Function to get Specific Jobs based on Search and Location on LinkedIn.
def get_jobs_specific(driver: webdriver.Chrome, search_query, location, timeline, easy_apply, page_count = 3, is_temp = False, suffix = ""):
    url = f"https://www.linkedin.com/jobs/search/?{"f_AL=true" if easy_apply else ""}{get_time_param(timeline)}&geoId={get_geo_id(location)}&keywords={search_query.replace(" ", "%20")}&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true&spellCorrectionEnabled=true"
    file_save_name = f"jobs_{get_geo_id(location)}_{timeline}_{easy_apply}_{search_query}{suffix}.csv"
    return get_jobs(driver, url, file_save_name, page_count, "Specific Job Search", is_temp)

# Function to get Jobs based on the Recommended Jobs on LinkedIn.
def get_jobs_recommended(driver, is_temp = False):
    url = "https://www.linkedin.com/jobs/collections/recommended/?"
    date = datetime.strftime(datetime.now(), '%d-%m-%Y')
    file_save_name = f"jobs_recommended_{date}.csv"
    return get_jobs(driver, url, file_save_name, 1, "Recommended Job Search", is_temp)

# Function to fetch the jobs and get information about them.
def get_jobs(driver: webdriver.Chrome, url, file_save_name = None, page_count = 3, info_message = "Job Search", should_delete = False):
    uid = str(uuid4())
    print(f"[INFO]\tUUID: {uid}")
    if should_delete:
        file_save_name = f"jobs_{uid}.csv"
    print(f"[INFO]\tFile Save Name: {file_save_name}")
    return_dict = {
        "uuid": uid,
        "job_data": [],
        "save_path": file_save_name
    }

    # Setup Resume for the User
    try:
        with open("resume.txt", "r") as f:
            resume = f.read()
    except:
        resume = ""

    # Setup Text Maker to get text from the HTML Elements.
    text_maker = html2text.HTML2Text()
    text_maker.ignore_links = True
    text_maker.ignore_images = True
    text_maker.wrap_links = True
    text_maker.wrap_lists = True

    print("[INFO]\tStarting job search.")
    for page in range(page_count):
        driver.get(url + f"&start={page * 25}")
        time.sleep(SLEEP_TIME * 5)

        # Get Jobs List for the Page.
        jobs_ul = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/div/div[2]/div[1]/div/ul')))
        jobs = jobs_ul.find_elements(By.XPATH, './li')

        # Process Jobs
        i = 0
        while i < len(jobs):
            try:
                jobs[i].click()
                time.sleep(SLEEP_TIME * 3)

                # Get Job Details
                job_a = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/div/div[2]/div[2]/div/div[2]/div/div/div[1]/div/div[1]/div/div[1]/div/div[2]/div/h1/a')))
                job_link = job_a.get_attribute("href")
                job_heading = job_a.get_attribute("innerText")
                job_heading = job_heading.replace(",", "")
                article = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/div/div[2]/div[2]/div/div[2]/div/div/div[1]/div/div[4]/article')))
                jd = text_maker.handle(article.get_attribute("innerHTML"))
            
                # Extract Job Information using Gemini AI
                try:
                    response = model.generate_content(f"""
                        The following is the job description. Parse it and provide the following details in a JSON format.
                        Return a JSON containing the company's name under the key 'company',
                        minimum years of experience as 'min_exp', maximum years of experience as 'max_exp'.
                        Use 'N/A' if the min and max exp is not available.
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
                        Generate only the JSON and nothing else.
                                                      
                        Job Description - 
                        {jd}"""
                    ).text
                    response = response[8:]
                    response = response[:-4]
                    job_data = json.loads(response)
                except Exception as e:
                    print(f"[ERROR]\t{e}")
                    print("[INFO]\tRPM exceeded. Waiting for 60 seconds.")
                    for _ in tqdm(range(60)):
                        time.sleep(1)
                    continue

                # Write Data to CSV
                job_data["link"] = job_link.split("?")[0]
                job_data["title"] = job_heading
                job_data['company'] = job_data['company'].replace(",", "")
                job_data["match_score"] = calculate_similarity(jd, resume)
                return_dict["job_data"].append(job_data)
                with open(file_save_name, "a") as f:
                    f.write(f"{job_data['title']},{job_data['company']},{job_data['min_exp']},{job_data['max_exp']},{job_data["overall"]},{job_data['primary']},{job_data['secondary']},{job_data['citizenship_required']},{job_data['security_clearance_required']},{job_data['visa_sponsorship']},{job_data["match_score"]},{job_data['link']}\n")
                print(f"[INFO]\t{info_message} - Page: {page + 1}, Job: {i + 1} completed.")
                i += 1
            except selenium.common.exceptions.TimeoutException as e:
                print(f"[ERROR]\tTimeout Exception")
                i += 1
                jobs[i].click()
                time.sleep(SLEEP_TIME * 5)
                i -= 1
                jobs[i].click()
                time.sleep(SLEEP_TIME * 5)
                try:
                    job_a = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/div/div[2]/div[2]/div/div[2]/div/div[1]/div/div[1]/div/div[1]/div/div[2]/div/h1/a')))
                    job_link = job_a.get_attribute("href")
                    print(f"[ERROR]\tCould not process {job_link}")
                    with open("error_links.txt", "a") as f:
                        f.write(f"{job_link}\n")
                except:
                    pass
                i += 1
            except Exception as e:
                print(f"[ERROR]\t{e}")
                try:
                    job_a = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/div/div[2]/div[2]/div/div[2]/div/div[1]/div/div[1]/div/div[1]/div/div[2]/div/h1/a')))
                    job_link = job_a.get_attribute("href")
                    print(f"[ERROR]\tCould not process {job_link}")
                    with open("error_links.txt", "a") as f:
                        f.write(f"{job_link}\n")
                except:
                    pass
                i += 1
                continue

    # Delete Temporary Files
    if should_delete:
        print("[INFO]\tDeleting temporary files.")
        os.remove(f"jobs_{uid}.csv")
    print("[INFO]\tJob search completed.")

    return return_dict

# Search Jobs Command
@click.command("search")
@click.option("--search_query", "-s", default="Software Engineer", help="The search query for the jobs.")
@click.option("--location", "-l", default="USA", help="The location for the jobs.")
@click.option("--timeline", "-t", default="24H", help="The timeline for the jobs.")
@click.option("--easy_apply", "-e", is_flag=True, help="Whether to only get jobs with easy apply.")
@click.option("--suffix", "-x", default="", help="The suffix for the file name.")
@click.option("--page_count", "-p", default=1, help="The number of pages to scrape.")
def search_jobs(search_query, location, timeline, easy_apply, suffix, page_count):
    driver = webdriver.Chrome(service=Service(CHROME_DRIVER_PATH))
    driver.maximize_window()
    login(driver)
    jobs_data = get_jobs_specific(driver, search_query, location, timeline, easy_apply, page_count, False, suffix)
    print(f"[INFO]\tJob Search Completed. The data has been saved at {jobs_data["save_path"]}.")
    driver.close()

# Search Recommended Jobs Command
@click.command("recommended")
def search_recommended_jobs():
    driver = webdriver.Chrome(service=Service(CHROME_DRIVER_PATH))
    driver.maximize_window()
    login(driver)
    jobs_data = get_jobs_recommended(driver, False)
    print(f"[INFO]\tJob Search Completed. The data has been saved at {jobs_data["save_path"]}.")
    driver.close()

# Daily Routine Command
@click.command("daily")
@click.option("--search_query", "-s", default="Software Engineer", help="The search query for the jobs.")
@click.option("--location", "-l", default="USA", help="The location for the jobs.")
@click.option("--easy_apply", "-e", is_flag=True, help="Whether to only get jobs with easy apply.")
@click.option("--yoe", "-y", default=2, help="How many years of experience you have.")
@click.option("--save", default=".", help="The path to save the data.")
def daily_routine(search_query, location, easy_apply, yoe, save):
    jobs_list = []
    driver = webdriver.Chrome(service=Service(CHROME_DRIVER_PATH))
    driver.maximize_window()
    login(driver)

    # Get Recommended Jobs
    jobs_list.extend(get_jobs_recommended(driver, True)["job_data"])

    # Get Specific Jobs
    timelines = [("24H", 2), ("7D", 1), ("1M", 1)]
    for timeline, page_count in timelines:
        jobs_list.extend(get_jobs_specific(driver, search_query, location, timeline, easy_apply, page_count, True)["job_data"])

    # Filter Jobs
    daily_jobs = []
    jobs_seen = set()
    for job in jobs_list:
        if not is_job_suitable(job, yoe):
            continue
        if job["link"] in jobs_seen:
            continue
        jobs_seen.add(job["link"])
        daily_jobs.append(job)

    # Save Data to CSV
    columns = ["title", "company", "min_exp", "max_exp", "age_match", "overall", "primary", "secondary", "citizenship_required", "security_clearance_required", "visa_sponsorship", "link"]
    df = pd.DataFrame(daily_jobs, columns=columns)
    file_name = f"jobs_DAILY_{datetime.strftime(datetime.now(), '%d-%m-%Y')}_{get_geo_id(location)}_{easy_apply}_{search_query}.csv"
    save_path = f"{save}/{file_name}"
    df.to_csv(save_path, index=False)
    print(f"[INFO]\tDaily Routine Completed. The data has been saved at {save_path}.")
    driver.close()

@click.group()
def cli():
    pass

cli.add_command(search_jobs)
cli.add_command(search_recommended_jobs)
cli.add_command(daily_routine)

if __name__ == "__main__":
    cli()