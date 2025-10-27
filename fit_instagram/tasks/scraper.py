#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import os

from fit_acquisition.tasks.task import Task
from fit_acquisition.tasks.task_worker import TaskWorker
from fit_common.gui.utils import Status
from PySide6.QtCore import Signal

from fit_instagram.lang import load_translations


class TaskInstagramScraperWorker(TaskWorker):
    scraped_status = Signal(object)

    def start(self):
        self.started.emit()

        methods_to_execute = self.options.get("methods_to_execute")
        service = self.options.get("instagram_service")
        profile_dir = self.options.get("profile_dir")

        if not os.path.exists(profile_dir):
            os.makedirs(profile_dir)

        service.set_dir(profile_dir)

        methods_to_execute = ["scrape_post"]

        for method in methods_to_execute:

            __scraped_status = {"method": method}
            method = getattr(service, method)

            try:
                method()
                __scraped_status["status"] = Status.SUCCESS
                __scraped_status["message"] = ""

            except Exception as e:
                __scraped_status["status"] = Status.FAILURE
                __scraped_status["message"] = str(e)

            self.scraped_status.emit(__scraped_status)

        self.finished.emit()


class TaskInstagramScraper(Task):
    scraped_status = Signal(object)

    def __init__(self, logger, progress_bar=None, status_bar=None):

        self.__translations = load_translations()

        super().__init__(
            logger,
            progress_bar,
            status_bar,
            label=self.__translations["INSTAGRAM_SCRAPER"],
            worker_class=TaskInstagramScraperWorker,
        )

        self.worker.scraped_status.connect(self.scraped_status.emit)

    def start(self):
        super().start_task(self.__translations["INSTAGRAM_SCRAPER_STARTED"])

    def _finished(self, status=Status.SUCCESS, details=""):
        message = self.__translations["INSTAGRAM_SCRAPER_COMPLETED"].format(status.name)
        super()._finished(status, details, message)
