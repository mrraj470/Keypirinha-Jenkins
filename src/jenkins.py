# Keypirinha launcher (keypirinha.com)

import base64
import json
import urllib.request

import keypirinha as kp
import keypirinha_util as kpu


class Config:
    """ Config section as model """
    DEFAULT_CATALOGUE_PREFIX = "Jenkins-"
    SECTION = "jenkins"

    def __init__(self, name: str, base_url: str, folders_to_scan: list,
                 username: str, api_token: str, searchable_as: str, enable_cache: bool):
        self.name = name
        self.base_url = base_url
        self.folders_to_scan = folders_to_scan
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
        self.cache = {}

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

    def on_suggest(self, user_input, items_chain):
        if not items_chain:
            return
        current_item = items_chain[-1]
        target = current_item.target()
        if target.startswith(Config.DEFAULT_CATALOGUE_PREFIX):
            config = [config for config in self.configs if Config.DEFAULT_CATALOGUE_PREFIX + config.name == target][0]
            self.set_suggestions(self._fetch_job_suggestion(config), kp.Match.FUZZY, kp.Sort.SCORE_DESC)

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
            if not settings.get("folders_to_scan", section=section, fallback=""):
                self.warn("Section '{}' doesn't have 'folders_to_scan' defined.".format(section))
                continue
            configs.append(Config(
                section_name,
                settings.get("jenkins_base_url", section=section, fallback="").strip("/"),
                settings.get("folders_to_scan", section=section, fallback="").split(","),
                settings.get("username", section=section, fallback="").strip(),
                settings.get("api_token", section=section, fallback="").strip(),
                settings.get("searchable_as", section=section, fallback="").strip(),
                settings.get_bool("enable_cache", section=section, fallback=True)
            ))
        return configs

    def _fetch_job_suggestion(self, config: Config):
        if config.name in self.cache:
            return self.cache[config.name]

        suggestions = []
        for folder in config.folders_to_scan:
            folder = folder.strip("/").replace("/", "/job/").strip()
            url = "{}/job/{}/api/json?tree=jobs[name,fullName,url]".format(config.base_url, folder)
            if not folder.strip():
                url = "{}/api/json?tree=jobs[name,fullName,url]".format(config.base_url)
            jobs = http_get_json(url, config.username, config.api_token)["jobs"]
            for job in jobs:
                suggestions.append(self.create_item(
                    category=kp.ItemCategory.URL,
                    label=job["name"],
                    short_desc=job["fullName"],
                    target=job["url"],
                    args_hint=kp.ItemArgsHint.FORBIDDEN,
                    hit_hint=kp.ItemHitHint.IGNORE
                ))
        if config.enable_cache:
            self.cache[config.name] = suggestions
        return suggestions


def http_get_json(url: str, username: str, token: str):
    request = urllib.request.Request(url)
    if username.strip() and token.strip():
        base64string = base64.b64encode((username + ":" + token).encode("ascii"))
        request.add_header("Authorization", "Basic {}".format(base64string.decode("ascii")))
    response = urllib.request.urlopen(request)
    return json.loads(response.read())
