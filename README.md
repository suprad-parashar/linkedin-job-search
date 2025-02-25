# LinkedIn Job Search Tool
In this highly competitive world, if you are trying to find a job, or just trying to switch to another job, best of luck! We all know how cutthroat the competition is. 

With this kind of competition, the best way to stand out would be to learn more, do more projects, and upskill yourself! However, who has the time? You need to apply to jobs, not just apply to them, but read the job description, see if it fits your profile, check if the job has any citizenship requirements, see if the company sponsors visa, etc. Too many things to do!!!

This is where my Automation comes in. It extracts all the necessary information such as minimum experience needed, citizenship requirements, and other stuff and gives you a list of jobs that you can actually apply to. No need to read the job description, just apply. It helps you in your search. (I wish it could apply automatically, but at this point, it's kinda really hard to implement.)

This script provides you with three commands - 

1. `search` - Searches for jobs based on a query, location, timeline, and other flags.
2. `recommended` - Provides you with a list of recommended jobs that matches your profile.
3. `daily` - Provides you with a daily digest of jobs that you can apply to!

## Setup and Installation
Clone this repo and install the dependencies.
```
pip install -r requirements.txt
```

Set up the Environment Variables by creating a `.env` file.
Add the following keys.
```
LINKEDIN_EMAIL = "sample@example.com"
LINKEDIN_PASSWORD = "VerySecurePassword!"
GEMINI_API_KEY="XXXXXXXXXXXXXXX"
CHROME_DRIVER_PATH = "/path/to/chromedriver"
GEMINI_MODEL_ID="gemini-2.0-flash" #latest
```

Create a `resume.txt` file and Copy and Paste your resume there. It will be used to check how good your resume fits for the job.
## Usage
Run the program with `--help` flag to know more about the commands and their usage.