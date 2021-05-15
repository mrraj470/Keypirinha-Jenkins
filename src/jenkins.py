# Keypirinha launcher (keypirinha.com)

import json

import keypirinha as kp
import keypirinha_net as kpnet


class Config:
    """ Config section as model """
    DEFAULT_CATALOGUE_PREFIX = "Jenkins-"
    SECTION = "jenkins"

    def __init__(self, name: str, base_url: str, folders_to_scan: list, custom_search_term: str):
        self.name = name
        self.base_url = base_url
        self.folders_to_scan = folders_to_scan
        self.custom_search_term = custom_search_term

    def get_catalogue_name(self):
        if not self.custom_search_term.strip():
            return self.DEFAULT_CATALOGUE_PREFIX + self.name
        return self.custom_search_term


class Jenkins(kp.Plugin):

    def __init__(self):
        super().__init__()
        self.configs = self._create_configs(self.load_settings())

    def on_start(self):
        pass

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
            self.set_suggestions(self._jenkins_job_suggestions(config), kp.Match.FUZZY, kp.Sort.SCORE_DESC)

    def on_execute(self, item, action):
        pass

    def on_activated(self):
        pass

    def on_deactivated(self):
        pass

    def on_events(self, flags):
        pass

    def _jenkins_job_suggestions(self, config: Config):
        suggestions = []
        suggestions.append(self.create_item(
            category=kp.ItemCategory.URL,
            label="Admin/Trigger",
            short_desc="Admin/Trigger job",
            target="http://localhost:8080/Jenkins/",
            args_hint=kp.ItemArgsHint.FORBIDDEN,
            hit_hint=kp.ItemHitHint.IGNORE
        ))
        return suggestions

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
                settings.get("custom_search_term", section=section, fallback="").strip()
            ))
        return configs

    def _fetch_job_suggestion(self, config: Config):
        suggestions = []
        for folder in config.folders_to_scan:
            jobs = http_get_json("{}/job/{}/api/json?tree[fullName,url]".format(config.base_url, folder))
            for job in jobs:
                suggestions.append(self.create_item(
                    category=kp.ItemCategory.URL,
                    label=job["fullName"],
                    short_desc=job["fullName"],
                    target=job["url"],
                    args_hint=kp.ItemArgsHint.FORBIDDEN,
                    hit_hint=kp.ItemHitHint.IGNORE
                ))


def http_get_json(url: str):
    opener = kpnet.build_urllib_opener()
    with opener.open(url) as request:
        response = request.load()
        return json.loads(response)
