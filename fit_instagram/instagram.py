# !/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

import logging
import os

from fit_acquisition.class_names import class_names
from fit_common.core import get_version
from fit_common.gui.error import Error
from fit_common.gui.spinner import Spinner
from fit_common.gui.ui_translation import translate_ui
from fit_common.gui.utils import Status
from fit_scraper.scraper import Scraper
from PySide6 import QtCore, QtWidgets

from fit_instagram.instagram_service import InstagramService
from fit_instagram.instagram_ui import Ui_fit_instagram
from fit_instagram.lang import load_translations
from fit_instagram.workers.login import InstagramLoginWorker
from fit_instagram.workers.logout import InstagramLogoutWorker


class Instagram(Scraper):
    def __init__(self, wizard=None):
        logger = logging.getLogger("scraper.instagram")
        packages = ["fit_instagram.tasks"]

        super().__init__(logger, "instagram", packages, wizard)

        if self.has_valid_case:
            class_names.register("INSTAGRAM_SCRAPER", "TaskInstagramScraper")
            self.acquisition.stop_tasks = [class_names.INSTAGRAM_SCRAPER]
            self.__translations = load_translations()
            self.__instagram_service = None
            self._is_logged_in = False
            self.__init_ui()
            translate_ui(self.__translations, self)

    def __init_ui(self):
        # HIDE STANDARD TITLE BAR
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self.ui = Ui_fit_instagram()
        self.ui.setupUi(self)
        self.__spinner = Spinner(self)

        # CUSTOM TOP BAR
        self.ui.left_box.mouseMoveEvent = self.move_window

        # MINIMIZE BUTTON
        self.ui.minimize_button.clicked.connect(self.showMinimized)

        # CLOSE BUTTON
        self.ui.close_button.clicked.connect(self.close)

        # CONFIGURATION BUTTON
        self.ui.configuration_button.clicked.connect(self.configuration_dialog)

        # CASE BUTTON
        self.ui.case_button.clicked.connect(self.show_case_info)

        # HIDE PROGRESS BAR
        self.ui.progress_bar.setValue(0)
        self.ui.progress_bar.setHidden(True)

        # HIDE STATUS MESSAGE
        self.ui.status_message.setHidden(True)

        # SET VERSION
        self.ui.version.setText(f"v{get_version()}")

        # SERVER INPUT FIELDS
        self.login_configuration_fields = self.ui.login_configuration.findChildren(
            QtWidgets.QLineEdit
        )
        for field in self.login_configuration_fields:
            field.textChanged.connect(self.__enable_login_button)

        self.ui.login_button.clicked.connect(self.__on_login_logout_clicked)
        self.ui.start_acquisition_button.clicked.connect(self.__start_acquisition)

        # ACQUISITION CRITERIA
        self.ui.acquisition_criteria.setEnabled(False)
        # ACQUISITION STATUS
        self.ui.acquisition_status.setEnabled(False)

        self.__uncheck_checkboxes()

    def mousePressEvent(self, event):
        self.dragPos = event.globalPosition().toPoint()

    def move_window(self, event):
        if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
            self.move(self.pos() + event.globalPosition().toPoint() - self.dragPos)
            self.dragPos = event.globalPosition().toPoint()
            event.accept()

    def __on_login_logout_clicked(self):
        if self._is_logged_in:
            self.__logout()
        else:
            self.__login()

    def __login(self):
        self.setEnabled(False)
        self.__spinner.start()

        self.__instagram_service = InstagramService()
        self._thread: QtCore.QThread | None = None
        self._worker: InstagramLoginWorker | None = None

        self._thread = QtCore.QThread()
        self._worker = InstagramLoginWorker()

        self._worker.options = dict()

        self._worker.options = {
            "auth_info": {
                "username": self.ui.username.text(),
                "password": self.ui.password.text(),
                "profile": self.ui.profile_name.text(),
            },
            "instagram_service": self.__instagram_service,
        }

        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.start)
        self._worker.finished.connect(self.__is_logged_in)
        self._worker.error.connect(self.__handle_error)

        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._worker.finished.connect(self._worker.deleteLater)

        self._worker.error.connect(self._thread.quit)
        self._worker.error.connect(self._worker.deleteLater)

        self._thread.start()

    def __is_logged_in(self, account_type):
        self.setEnabled(True)
        self.__spinner.stop()
        self._is_logged_in = True
        self.ui.login_button.setText(self.__translations["LOGOUT_BUTTON"])
        self.__enable_login_configuration_fields(False)
        self.__enable_acquisition_checkbox_from_account_type(account_type)
        self.ui.acquisition_status_list.clear()
        self.ui.start_acquisition_button.setEnabled(True)
        self.ui.acquisition_status.setEnabled(True)
        self.__uncheck_checkboxes()

    def __logout(self):
        self.setEnabled(False)
        self.__spinner.start()
        self._thread: QtCore.QThread | None = None
        self._worker: InstagramLogoutWorker | None = None

        self._thread = QtCore.QThread()
        self._worker = InstagramLogoutWorker()

        self._worker.options = dict()
        self._worker.options = {
            "instagram_service": self.__instagram_service,
        }
        self._is_logged_in = False
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.start)
        self._worker.finished.connect(self.__is_logged_out)
        self._worker.error.connect(self.__handle_error)

        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._worker.finished.connect(self._worker.deleteLater)

        self._worker.error.connect(self._thread.quit)
        self._worker.error.connect(self._worker.deleteLater)

        self._thread.start()

    def __is_logged_out(self):
        self.setEnabled(True)
        self.__spinner.stop()
        self._is_logged_in = False
        self.ui.login_button.setText(self.__translations["LOGIN_BUTTON"])
        self.__enable_login_configuration_fields(True)
        self.__instagram_service = None
        self.ui.acquisition_status_list.clear()
        self.ui.login_button.setText(self.__translations["LOGIN_BUTTON"])
        self.ui.start_acquisition_button.setEnabled(False)
        self.ui.acquisition_status.setEnabled(False)

    def __start_acquisition(self):
        self.setEnabled(True)
        self.__spinner.start()
        self.ui.acquisition_status_list.clear()

        methods_to_execute = ["scrape_profile_picture", "scrape_info"]
        checkboxes = self.ui.acquisition_criteria.findChildren(QtWidgets.QCheckBox)

        checkboxes_checked = list(
            filter(lambda checkbox: checkbox.isChecked(), checkboxes)
        )
        for checkbox in checkboxes_checked:
            methods_to_execute.append(checkbox.objectName())

        self.__spinner.stop()

        if self.create_acquisition_directory():
            self.acquisition.options = {
                "type": "instagram",
                "case_info": self.case_info,
                "acquisition_directory": self.acquisition_directory,
                "instagram_service": self.__instagram_service,
                "methods_to_execute": methods_to_execute,
                "profile_dir": os.path.join(
                    self.acquisition_directory,
                    self.ui.profile_name.text(),
                ),
            }

            self.execute_start_tasks_flow()

    def on_start_tasks_finished(self):
        task = self.acquisition.tasks_manager.get_task("TaskInstagramScraper")
        if task:
            task.scraped_status.connect(self.__scraped_status)

        self.ui.status_message.setText("")
        self.ui.status_message.setHidden(True)

        return self.execute_stop_tasks_flow()

    def on_post_acquisition_finished(self):
        self.__uncheck_checkboxes()
        return super().on_post_acquisition_finished()

    def __enable_acquisition_checkbox_from_account_type(self, account_type):

        if account_type == 1:
            self.ui.acquisition_criteria.setEnabled(True)
            self.ui.acquisition_status.setEnabled(True)
        elif account_type == 2 or account_type == 4:
            self.ui.scrape_saved_posts.setEnabled(False)
            self.ui.acquisition_criteria.setEnabled(True)
            self.ui.acquisition_status.setEnabled(True)

    def __handle_error(self, error):
        self.setEnabled(True)
        self.__spinner.stop()
        dialog = Error(
            QtWidgets.QMessageBox.Icon.Critical,
            error.get("title"),
            error.get("msg"),
            error.get("details"),
        )
        dialog.exec()

    def __enable_login_button(self):
        all_field_filled = all(
            input_field.text() for input_field in self.login_configuration_fields
        )
        self.ui.login_button.setEnabled(all_field_filled)

    def __enable_login_configuration_fields(self, enable):
        for input_field in self.login_configuration_fields:
            input_field.setEnabled(enable)

    def __uncheck_checkboxes(self):
        for checkbox in self.ui.acquisition_criteria.findChildren(QtWidgets.QCheckBox):
            if checkbox.isChecked():
                checkbox.setChecked(False)

    def __scraped_status(self, info):

        __acquisition_name = None
        __method = info.get("method")

        if __method == "scrape_profile_picture":
            __acquisition_name = self.__translations["PROFILE_PIC"]
        elif __method == "scrape_info":
            __acquisition_name = [
                self.__translations["FULL_NAME"],
                self.__translations["BIO"],
                self.__translations["POST_NUMBER"],
                self.__translations["ACCOUNT_TYPE"],
            ]
        else:
            checkbox = self.ui.acquisition_criteria.findChild(
                QtWidgets.QCheckBox, info.get("method")
            )

            if checkbox:
                __acquisition_name = checkbox.text()

        if __acquisition_name is not None:

            if isinstance(__acquisition_name, str):
                label_text = self.__get_acquisition_label_text(
                    __acquisition_name, info.get("status"), info.get("message")
                )
                self.__add_label_in_acquisition_status_list(label_text)

            if isinstance(__acquisition_name, list):
                for name in __acquisition_name:
                    label_text = self.__get_acquisition_label_text(
                        name, info.get("status"), info.get("message")
                    )
                    self.__add_label_in_acquisition_status_list(label_text)

    def __get_acquisition_label_text(
        self, acquisition_name, acquisition_status, acquisition_message
    ):
        __status = (
            '<strong style="color:green">{}</strong>'.format(acquisition_status)
            if acquisition_status == Status.SUCCESS
            else '<strong style="color:red">{}</strong>'.format(acquisition_status)
        )
        __message = (
            ""
            if acquisition_message == ""
            else "details: {}".format(acquisition_message)
        )

        return "Acquisition {}: {} {}".format(acquisition_name, __status, __message)

    def __add_label_in_acquisition_status_list(self, label_text):
        item = QtWidgets.QListWidgetItem(self.ui.acquisition_status_list)
        label = QtWidgets.QLabel(label_text)
        label.setWordWrap(True)
        item.setSizeHint(label.sizeHint())
        self.ui.acquisition_status_list.addItem(item)
        self.ui.acquisition_status_list.setItemWidget(item, label)
