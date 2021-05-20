# Keypirinha launcher (keypirinha.com)

import base64
import json
import re
import urllib.request

import keypirinha as kp
import keypirinha_util as kpu

from .helper import Cache


class Config:
    """ Config section as model """
    DEFAULT_CATALOGUE_PREFIX = "Jenkins-"
    SECTION = "jenkins"

    def __init__(self, name: str, base_url: str, search_starts_from: list,
                 username: str, api_token: str, searchable_as: str, enable_cache: bool):
        self.name = name
        self.base_url = base_url
        self.search_starts_from = search_starts_from
        self.username = username
        self.api_token = api_token
        self.searchable_as = searchable_as
        self.enable_cache = enable_cache

    def get_catalogue_name(self):
        if not self.searchable_as.strip():
            return self.DEFAULT_CATALOGUE_PREFIX + self.name
        return self.searchable_as


class Jenkins(kp.Plugin):
    def __init__(self):
        super().__init__()
        self.configs = self._create_configs(self.load_settings())
        self.cache = Cache(self.get_package_cache_path(create=True))

    def on_start(self):
        self.cache.clear()

    def on_catalog(self):
        suggestions = []
        for config in self.configs:
            suggestions.append(self.create_item(
                category=kp.ItemCategory.KEYWORD,
                label=config.get_catalogue_name() + ":",
                short_desc="Search and launch '{}' Jenkins jobs...".format(config.name),
                target=Config.DEFAULT_CATALOGUE_PREFIX + config.name,
                args_hint=kp.ItemArgsHint.REQUIRED,
                hit_hint=kp.ItemHitHint.IGNORE
            ))
        self.set_catalog(suggestions)

    def on_suggest(self, user_input, items_chain: list):
        if not items_chain:
            return
        current_item = items_chain[-1]
        first_item = items_chain[0]
        current_target = current_item.target()
        first_target = first_item.target()

        if current_target.startswith(Config.DEFAULT_CATALOGUE_PREFIX):
            config = \
                [config for config in self.configs if Config.DEFAULT_CATALOGUE_PREFIX + config.name == current_target][
                    0]
            self.set_suggestions(self._get_main_suggestions(config), kp.Match.FUZZY, kp.Sort.SCORE_DESC)
        elif len(items_chain) > 1 and first_target.startswith(Config.DEFAULT_CATALOGUE_PREFIX):
            config = \
                [config for config in self.configs if Config.DEFAULT_CATALOGUE_PREFIX + config.name == first_target][
                    0]
            self.set_suggestions(self._get_sub_suggestions(config, current_item.short_desc()), kp.Match.FUZZY,
                                 kp.Sort.SCORE_DESC)

    def on_execute(self, item, action):
        kpu.execute_default_action(self, item, action)

    def on_activated(self):
        pass

    def on_deactivated(self):
        pass

    def on_events(self, flags):
        if flags & kp.Events.PACKCONFIG:
            self.log("reloading due to config change...")
            self.__init__()
            self.on_start()
            self.on_catalog()
            self.log("reloading done...")

    def _create_configs(self, settings):
        configs = []
        for section in settings.sections():
            if section.lower().startswith(Config.SECTION + "/"):
                section_name = section[len(Config.SECTION) + 1:].strip()
            else:
                continue
            if not len(section_name):
                self.warn("Ignoring empty jenkins section")
                continue
            if not settings.get("jenkins_base_url", section=section, fallback=""):
                self.warn("Section '{}' doesn't have 'jenkins_base_url' defined.".format(section))
                continue
            configs.append(Config(
                section_name,
                settings.get("jenkins_base_url", section=section, fallback="").strip("/"),
                settings.get("search_starts_from", section=section, fallback="/").split(","),
                settings.get("username", section=section, fallback="").strip(),
                settings.get("api_token", section=section, fallback="").strip(),
                settings.get("searchable_as", section=section, fallback="").strip(),
                settings.get_bool("enable_cache", section=section, fallback=True)
            ))
        return configs

    def _get_main_suggestions(self, config: Config):
        jobs_response = []
        if self.cache.exists(config.name):
            # using cached json response
            jobs_response = self.cache.fetch_object(config.name)
        else:
            for folder in config.search_starts_from:
                folder = folder.strip("/").replace("/", "/job/").strip()
                url = "{}/job/{}/api/json?tree=jobs[name,fullName,url]".format(config.base_url, folder)
                if not folder.strip():
                    url = "{}/api/json?tree=jobs[name,fullName,url]".format(config.base_url)
                jobs = http_get_json(url, config.username, config.api_token)["jobs"]
                jobs_response.extend(jobs)
        suggestions = self._create_job_items(jobs_response)
        if config.enable_cache:
            # saving response in plugin cache dir
            self.cache.save_object(jobs_response, config.name)
        return suggestions

    def _get_sub_suggestions(self, config: Config, folder: str):
        folder = folder.strip("/").replace("/", "/job/").strip()
        url = "{}/job/{}/api/json?tree=jobs[name,fullName,url]".format(config.base_url, folder)
        if not folder.strip():
            url = "{}/api/json?tree=jobs[name,fullName,url]".format(config.base_url)
        jobs = http_get_json(url, config.username, config.api_token)["jobs"]
        return self._create_job_items(jobs)

    def _create_job_items(self, jobs: list):
        suggestions = []
        for job in jobs:
            job_type = re.sub(r".*\.", "", job["_class"])
            if job_type in ["FreeStyleProject", "WorkflowJob"]:
                suggestions.append(self.create_item(
                    category=kp.ItemCategory.URL,
                    label=job["name"],
                    short_desc=job["fullName"],
                    target=job["url"],
                    args_hint=kp.ItemArgsHint.FORBIDDEN,
                    hit_hint=kp.ItemHitHint.IGNORE
                ))
            else:
                suggestions.append(self.create_item(
                    category=kp.ItemCategory.URL,
                    label=job["name"] + " (Folder)",
                    short_desc=job["fullName"],
                    target=job["url"],
                    args_hint=kp.ItemArgsHint.REQUIRED,
                    hit_hint=kp.ItemHitHint.IGNORE
                ))
        return suggestions


def http_get_json(url: str, username: str, token: str):
    request = urllib.request.Request(url)
    if username.strip() and token.strip():
        base64string = base64.b64encode((username + ":" + token).encode("ascii"))
        request.add_header("Authorization", "Basic {}".format(base64string.decode("ascii")))
    response = urllib.request.urlopen(request)
    return json.loads(response.read())
