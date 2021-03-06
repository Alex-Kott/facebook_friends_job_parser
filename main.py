import csv
import re
from collections import defaultdict
from dataclasses import dataclass
from random import randint
from typing import List, Tuple
from time import sleep

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement


def delay():
    return randint(3, 13)


@dataclass
class User:
    link: str
    name: str
    jobs: List[str]
    friends: List['User']

    def __init__(self, friend_item):
        self.link = User.get_link_from_item(friend_item)
        self.name = User.get_name_from_item(friend_item)
        self.jobs = []
        self.friends = []

    def add_jobs(self, jobs: List[str]) -> None:
        self.jobs.extend(jobs)

    @staticmethod
    def get_link_from_item(friend_item: WebElement) -> str:
        user_link = friend_item.find_elements_by_class_name("fsl")[0] \
                               .find_element_by_tag_name("a") \
                               .get_attribute("href")

        if user_link.find("profile.php") == -1:
            return user_link.split('?')[0]
        else:
            user_id = re.findall(r'(?<=id=)\d+', user_link)[0]

            return f"https://www.facebook.com/profile.php?id={user_id}"

    @staticmethod
    def get_name_from_item(friend_item: WebElement) -> str:
        return friend_item.find_elements_by_class_name("fsl")[0].text


def get_profile_links() -> List[str]:
    with open(profile_links_file) as file:
        return [line.strip('\n') for line in file.readlines()]


def scroll_page(driver: Chrome, height: str):
    driver.find_element_by_tag_name("body").send_keys(Keys.END)
    sleep(3)
    if height != driver.execute_script("return document.body.scrollHeight"):
        scroll_page(driver, driver.execute_script("return document.body.scrollHeight"))


def parse_friends(driver: Chrome, user_link: str) -> List[User]:
    sleep(delay())
    driver.get(f"{user_link}/friends")
    driver.find_element_by_tag_name("body").send_keys(Keys.ESCAPE)
    scroll_page(driver, driver.execute_script("return document.body.scrollHeight"))

    friend_items = driver.find_elements_by_class_name("_698")
    friend_list = [User(friend_item) for friend_item in friend_items]

    return friend_list


def get_driver() -> Chrome:
    options = ChromeOptions()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless")

    return Chrome("./webdriver/chromedriver", chrome_options=options)


def get_fb_credentials() -> Tuple[str, str]:
    with open("fb_accounts.txt") as file:
        for line in file.readlines():
            credentials = line.strip('\n').split(";")
            yield credentials[0], credentials[1]


def is_suspended(driver: Chrome) -> bool:
    if driver.page_source.find("We want to make sure that your account is secure") != -1:
        return True
    return False


def facebook_login(driver: Chrome) -> None:
    sleep(3)
    fb_login, fb_password = next(fb_credentials)
    driver.get("https://www.facebook.com")
    driver.find_element_by_id("email").send_keys(fb_login)
    driver.find_element_by_id("pass").send_keys(fb_password)
    driver.find_element_by_id("pass").send_keys(Keys.ENTER)
    # driver.find_element_by_id("u_0_3").click()
    driver.find_element_by_tag_name("body").send_keys(Keys.ESCAPE)
    sleep(1)

    if is_suspended(driver):
        facebook_logout(driver)
        facebook_login(driver)


def facebook_logout(driver: Chrome) -> None:
    sleep(2)
    driver.get("https://www.facebook.com")
    driver.find_element_by_tag_name("body").send_keys(Keys.ESCAPE)
    try:
        driver.find_element_by_id("userNavigationLabel").click()
        sleep(1)
        driver.find_element_by_class_name("_64kz").click()
    except:
        sleep(1)
        driver.get("https://www.facebook.com/logout.php?h=Afc_DcWNH6_gvpKo&t=1534745122&ref=mb")
        # driver.find_element_by_class_name("_2t-f").click()
    sleep(1)


def parse_job(item: WebElement) -> str:
    text = item.text.split('\n')
    job_place = text[0]
    if len(text) > 1:
        job_position = text[1].split(' ·')[0]
    else:
        job_position = 'Нет данных'

    return f"{job_place} ({job_position})"


def parse_friend_jobs(driver: Chrome, friends_list: List[User]):
    for user in friends_list:
        try:
            if user.link in parsed_user_links:
                print(user.link)
                continue
            user.add_jobs(parse_jobs(driver, user.link))
            save_user(user)
        except NoSuchElementException:
            facebook_logout(driver)
            try:
                facebook_login(driver)
            except:
                facebook_logout(driver)
                facebook_login(driver)
            with open("log.txt", "a") as file:
                file.write(f"{user.link}\n")


def parse_friends_works(driver: Chrome, links: List[str]) -> defaultdict:
    data = defaultdict(list)
    for profile_link in links:
        file_name = profile_link.split('/')[-1]
        friends_list = parse_friends(driver, profile_link)
        parse_friend_jobs(driver, friends_list)

        data[profile_link] = friends_list

    return data


def save_to_csv(data: defaultdict) -> None:
    with open("data.csv", "w", encoding="utf-8") as file:
        csv_write = csv.writer(file, delimiter=';', )
        for profile_link, users in data.items():
            for user in users:
                csv_write.writerow([profile_link, f"{user.name} ({user.link})", *user.jobs[:2]])


def save_user(user: User):
    print(user)
    with open(users_file, "a", encoding="utf-8") as file:
        csv_write = csv.writer(file, delimiter=';', )
        csv_write.writerow([user.name, user.link, *user.jobs[:2]])


def get_parsed_links():
    with open(users_file) as file:
        return [line.split(';')[0].strip('\n') for line in file.readlines()]


def save_friends(driver: Chrome, profile_links):
    for profile_link in profile_links:
        print(f"Start parce friends: {profile_link}")
        friends_list = parse_friends(driver, profile_link)

        file_name = profile_link.split('/')[-1]
        with open(f"{file_name}_friends.txt", "w") as file:
            for friend in friends_list:
                file.write(f"{friend.link}; {friend.name}\n")


def parse_jobs(driver: Chrome, user_link: str) -> List[str]:
    sleep(delay())
    driver.get(user_link)
    driver.find_element_by_tag_name("body").send_keys(Keys.ESCAPE)  # закроем поп-ап с предложением об оповещениях
    driver.find_element(By.XPATH, "//a[@data-tab-key='about']").click()
    sleep(delay())
    driver.find_element(By.XPATH, "//a[@data-testid='nav_edu_work']").click()
    sleep(delay())
    experience_list = driver.find_elements_by_class_name("experience")
    jobs = [parse_job(item) for item in experience_list]

    return jobs


def get_friend_links(profile_link: str) -> List:
    file_name = profile_link.split('/')[-1]
    with open(f"{file_name}_friends.txt") as file:
        return [line.split(';')[0].strip('\n') for line in file.readlines()]


def save_jobs(friend_link, jobs):
    print(friend_link, jobs)
    with open("users.txt", "a") as file:
        file.write(f"{friend_link};{';'.join(jobs)}\n")


def main(driver: Chrome):
    profile_links = get_profile_links()

    facebook_login(driver)

    for profile_link in profile_links:
        friend_links = get_friend_links(profile_link)

        for friend_link in friend_links:
            try:
                if friend_link in parsed_user_links:
                    continue
                try:
                    jobs = parse_jobs(driver, friend_link)
                except:
                    continue
                save_jobs(friend_link, jobs)
            except NoSuchElementException:
                facebook_logout(driver)
                try:
                    facebook_login(driver)
                except:
                    facebook_logout(driver)
                    facebook_login(driver)
                with open("log.txt", "a") as file:
                    file.write(f"{friend_link}\n")


if __name__ == "__main__":
    profile_links_file = "target_users.txt"
    users_file = "users.txt"

    fb_credentials = get_fb_credentials()
    parsed_user_links = get_parsed_links()

    chrome_driver = get_driver()
    try:
        main(chrome_driver)
    except Exception as e:
        print(e)
        chrome_driver.close()
