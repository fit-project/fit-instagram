#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######
import os
import shutil
import time
from datetime import datetime, timezone
from urllib.request import urlopen

from fit_common.core import debug, get_context, log_exception
from instaloader import Profile, instaloader

from fit_instagram.lang import load_translations

# Override default handle_429 behavior to manage error 429 by UI.
# https://instaloader.github.io/module/instaloadercontext.html#instaloader.RateController
# https://instaloader.github.io/troubleshooting.html#too-many-requests
# “Too many queries in the last time” is not an error.
# It is a notice that the rate limit has almost been reached, according to Instaloader’s
# own rate accounting mechanism.Instaloader allows to adjust the rate controlling behavior by overriding instaloader.RateController
# instagram_service.py (o dove risiede la tua classe)


class InstagramRateController(instaloader.RateController):

    def __init__(self, ctx, *, max_wait_seconds: int = 300, min_wait_seconds: int = 5):
        super().__init__(ctx)
        self.max_wait_seconds = max_wait_seconds
        self.min_wait_seconds = min_wait_seconds

    def handle_429(self, query_type: str) -> None:
        waited = 0

        while waited < self.max_wait_seconds:
            try:
                delay = self.get_sleep() or 0
            except Exception:
                delay = 0

            delay = max(delay, self.min_wait_seconds)

            time.sleep(delay)
            return

        from fit_instagram.lang import load_translations

        __t = load_translations()
        raise Exception(__t["HANDLE_429"])


class InstagramService:
    def __init__(self):
        self.loader = instaloader.Instaloader(
            rate_controller=lambda ctx: InstagramRateController(
                ctx, max_wait_seconds=600, min_wait_seconds=10
            )
        )
        self.profile = None
        self.profile_from_username = None
        self.username = None
        self.password = None
        self.profile_name = None
        self.is_logged_in = False
        self.__translations = load_translations()

    def set_login_information(self, username, password, profile_name):
        self.username = username
        self.password = password
        self.profile_name = profile_name

    def login(self):
        self.loader.login(self.username, self.password)
        try:
            self.profile = Profile.from_username(self.loader.context, self.profile_name)
            self.is_logged_in = True

        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Login failed",
                str(e),
                context=get_context(self),
            )
            raise Exception(e)

    def set_dir(self, path):
        self.path = path
        self.loader.dirname_pattern = self.path

    def scrape_post(self):
        try:
            posts = self.profile.get_posts()
            self.__set_loader_dirname_pattern("posts")
            for post in posts:
                self.loader.download_post(post, self.profile)
            self.__set_loader_dirname_pattern()
        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Scrape post failed",
                str(e),
                context=get_context(self),
            )
            raise Exception(e)

    def scrape_stories(self):
        try:
            id = []
            id.append(self.profile.userid)
            self.__set_loader_dirname_pattern("stories")
            self.loader.download_stories(id)
            self.__set_loader_dirname_pattern()
        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Scrape stories failed",
                str(e),
                context=get_context(self),
            )
            raise Exception(e)

    def scrape_followers(self):
        try:
            n_followers = self.profile.followers
            followers = self.profile.get_followers()
            file = open(
                os.path.join(
                    self.__make_scraped_type_directory("followers"), "followers.txt"
                ),
                "w",
                encoding="utf-8",
            )
            file.write(self.__translations["N_FOLLOWERS"] + str(n_followers) + "\n")
            file.write("\n")
            file.write(self.__translations["FOLLOWERS"])
            for follower in followers:
                file.write(follower.username + "\n")
            file.close()
        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Scrape followers failed",
                str(e),
                context=get_context(self),
            )
            raise Exception(e)

    def scrape_followees(self):
        try:
            n_followees = self.profile.followees
            followees = self.profile.get_followees()

            file = open(
                os.path.join(
                    self.__make_scraped_type_directory("followees"), "followees.txt"
                ),
                "w",
                encoding="utf-8",
            )
            file.write(self.__translations["N_FOLLOWEES"] + str(n_followees) + "\n")
            file.write("\n")
            file.write(self.__translations["SCRAPE_FOLLOWEES"])
            for followee in followees:
                file.write(followee.username + "\n")
            file.close()
        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Scrape followees failed",
                str(e),
                context=get_context(self),
            )
            raise Exception(e)

    def scrape_saved_posts(self):
        try:
            tmp_context_username = None

            if self.profile.username != self.profile._context.username:
                tmp_context_username = self.profile._context.username
                self.profile._context.username = self.profile.username

            saved_posts = self.profile.get_saved_posts()

            if tmp_context_username is not None:
                self.profile._context.username = tmp_context_username

            self.__set_loader_dirname_pattern("saved_posts")
            for saved_post in saved_posts:
                self.loader.download_post(saved_post, self.profile_name)
            self.__set_loader_dirname_pattern()
        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Scrape saved posts failed",
                str(e),
                context=get_context(self),
            )
            raise Exception(e)

    def scrape_profile_picture(self):
        try:
            target_dir = self.__make_scraped_type_directory("profile_pic")
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S_UTC")
            filename = f"{ts}_profile_pic.jpg"
            filepath = os.path.join(target_dir, filename)

            pic_url = str(self.profile.profile_pic_url)

            with urlopen(pic_url) as resp, open(filepath, "wb") as out:
                shutil.copyfileobj(resp, out)

        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Profile picture download failed",
                str(e),
                context=get_context(self),
            )
            raise Exception(e)

    def scrape_tagged_posts(self):
        try:
            tagged_posts = self.profile.get_tagged_posts()
            self.__set_loader_dirname_pattern("tagged_posts")
            for tagged_post in tagged_posts:
                self.loader.download_post(tagged_post, self.profile_name)
            self.__set_loader_dirname_pattern()
        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Scrape tagged posts failed",
                str(e),
                context=get_context(self),
            )
            raise Exception(e)

    def scrape_info(self):
        verified = self.profile.is_verified
        full_name = self.profile.full_name
        business_category = self.profile.business_category_name
        biography = self.profile.biography
        n_media = self.profile.mediacount
        file = open(
            os.path.join(
                self.__make_scraped_type_directory("profile_info"), "profile_info.txt"
            ),
            "w",
            encoding="utf-8",
        )
        if verified:
            file.write(self.__translations["PROFILE_TYPE_VERIFIED"] + "\n")
        else:
            file.write(self.__translations["PROFILE_TYPE_NO_VERIFIED"] + "\n")
        file.write(self.__translations["FULL_NAME"] + ":" + full_name + "\n")
        if not business_category:
            file.write(self.__translations["PROFILE_TYPE_PERSONAL"] + "\n")
        else:
            file.write(
                self.__translations["ACCOUNT_TYPE"]
                + ":"
                + str(business_category)
                + "\n"
            )
        file.write(self.__translations["BIO"] + biography + "\n")
        file.write(self.__translations["POST_NUMBER"] + str(n_media))
        file.flush()
        file.close()

    def scrape_highlights(self):
        try:
            self.__set_loader_dirname_pattern("highlights")
            self.loader.download_highlights(self.profile.userid)
            self.__set_loader_dirname_pattern()
        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Scrape highlights failed",
                str(e),
                context=get_context(self),
            )
            raise Exception(e)

    def __make_scraped_type_directory(self, directory_name):
        scraped_type_directory = os.path.join(self.path, directory_name)
        if not os.path.exists(scraped_type_directory):
            os.makedirs(scraped_type_directory)

        return scraped_type_directory

    def __set_loader_dirname_pattern(self, directory_name=None):
        if directory_name is None:
            self.loader.dirname_pattern = self.path
        else:
            self.loader.dirname_pattern = self.__make_scraped_type_directory(
                directory_name
            )

    def create_zip(self, path):
        for folder in os.listdir(path):
            folder_path = os.path.join(path, folder)
            if os.path.isdir(folder_path):
                shutil.make_archive(folder_path, "zip", folder_path)
                shutil.rmtree(folder_path)

    def check_account(self):
        if self.username != self.profile_name:
            try:
                self.profile = Profile.from_username(
                    self.loader.context, self.profile_name
                )
            except Exception as e:
                log_exception(e, context=get_context(self))
                debug(
                    "Check account failed",
                    str(e),
                    context=get_context(self),
                )
                raise Exception(e)

            if self.profile.is_private:
                followers = self.profile.followers
                if followers == 0:
                    # CASE 3: we can only scrape basic information
                    return 3
                else:
                    # CASE 2: we can scrape all but not saved posts
                    return 2
            else:
                # CASE 4: we can scrape all but not saved posts
                return 4
        else:
            # CASE 1: we can scrape all
            return 1

    def logout(self):
        removed = []

        candidates = set()

        if self.username:
            candidates.update(
                {
                    f"{self.username}.session",
                    f"session-{self.username}",
                }
            )

            if hasattr(self, "path") and self.path:
                candidates.update(
                    {
                        os.path.join(self.path, f"{self.username}.session"),
                        os.path.join(self.path, f"session-{self.username}"),
                    }
                )

            home = os.path.expanduser("~")
            candidates.add(
                os.path.join(home, ".config", "instaloader", f"session-{self.username}")
            )  # Linux/macOS
            appdata = os.getenv("APPDATA")  # Windows Roaming
            if appdata:
                candidates.add(
                    os.path.join(appdata, "instaloader", f"session-{self.username}")
                )
            localappdata = os.getenv("LOCALAPPDATA")  # Windows Local
            if localappdata:
                candidates.add(
                    os.path.join(
                        localappdata, "instaloader", f"session-{self.username}"
                    )
                )

        for p in list(candidates):
            try:
                if p and os.path.exists(p):
                    os.remove(p)
                    removed.append(p)
            except Exception as e:
                log_exception(e, context=get_context(self))
                debug(
                    "Logout failed",
                    str(e),
                    context=get_context(self),
                )
                raise Exception(e)

        try:
            self.loader.close()
        except Exception as e:
            log_exception(e, context=get_context(self))
            debug(
                "Logout failed",
                str(e),
                context=get_context(self),
            )
            try:
                self.loader.context.close()
            except Exception as e:
                log_exception(e, context=get_context(self))
                debug(
                    "Logout failed",
                    str(e),
                    context=get_context(self),
                )
                raise Exception(e)

        self.profile = None
        self.profile_from_username = None
        self.is_logged_in = False

        return removed
