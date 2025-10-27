#!/usr/bin/env python3
# -*- coding:utf-8 -*-
######
# -----
# Copyright (c) 2023 FIT-Project
# SPDX-License-Identifier: GPL-3.0-only
# -----
######

from fit_acquisition.tasks.task_worker import TaskWorker
from instaloader.exceptions import (
    BadCredentialsException,
    ConnectionException,
    InvalidArgumentException,
    ProfileNotExistsException,
    QueryReturnedBadRequestException,
    QueryReturnedForbiddenException,
    QueryReturnedNotFoundException,
    TwoFactorAuthRequiredException,
)
from PySide6.QtCore import Signal

from fit_instagram.lang import load_translations


class InstagramLoginWorker(TaskWorker):
    finished = Signal(int)

    def __init__(self):
        super().__init__()
        self.__translations = load_translations()

    def start(self):
        auth_info = self.options.get("auth_info")
        service = self.options.get("instagram_service")
        __account_type = 0

        service.set_login_information(
            auth_info.get("username"),
            auth_info.get("password"),
            auth_info.get("profile"),
        )

        if service.is_logged_in is False:
            try:
                service.login()
                __account_type = service.check_account()
                self.finished.emit(__account_type)

            except BadCredentialsException as e:
                self.error.emit(
                    {
                        "title": self.__translations["LOGIN_ERROR_TITLE"],
                        "msg": self.__translations["PASSWORD_ERROR_MESSAGE"],
                        "details": str(e),
                    }
                )
            except TwoFactorAuthRequiredException as e:
                self.error.emit(
                    {
                        "title": self.__translations["LOGIN_ERROR_TITLE"],
                        "msg": self.__translations["TWO_FACTOR_REQUIRED_ERROR_MESSAGE"],
                        "details": str(e),
                    }
                )
            except ConnectionException as e:
                self.error.emit(
                    {
                        "title": self.__translations["LOGIN_ERROR_TITLE"],
                        "msg": self.__translations["CONNECTION_ERROR_MESSAGE"],
                        "details": str(e),
                    }
                )
            except (ProfileNotExistsException, QueryReturnedNotFoundException) as e:
                self.error.emit(
                    {
                        "title": self.__translations["LOGIN_ERROR_TITLE"],
                        "msg": self.__translations["INVALID_PROFILE_ERROR_MESSAGE"],
                        "details": str(e),
                    }
                )
            except (
                InvalidArgumentException,
                QueryReturnedBadRequestException,
                QueryReturnedForbiddenException,
            ) as e:
                self.error.emit(
                    {
                        "title": self.__translations["LOGIN_ERROR_TITLE"],
                        "msg": self.__translations["GENERIC_ERROR_MESSAGE"],
                        "details": str(e),
                    }
                )
            except Exception as e:
                self.error.emit(
                    {
                        "title": self.__translations["LOGIN_ERROR_TITLE"],
                        "msg": self.__translations["GENERIC_ERROR_MESSAGE"],
                        "details": str(e),
                    }
                )
