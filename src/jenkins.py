# Keypirinha launcher (keypirinha.com)

import base64
import json
import re
import urllib.request

import keypirinha as kp
import keypirinha_util as kpu

from .helper import Cache


class JenkinsConfig:
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

    def get_store_name(self) -> str:
        return self.SECTION + "_" + self.name


class AgentConfig:
    """ Config section as model """
    DEFAULT_CATALOGUE_PREFIX = "Agent-"
    SECTION = "agent"

    def __init__(self, name: str, base_url: str, username: str,
                 api_token: str, searchable_as: str):
        self.name = name
        self.base_url = base_url
        self.username = username
        self.api_token = api_token
        self.searchable_as = searchable_as

    def get_catalogue_name(self):
        if not self.searchable_as.strip():
            return self.DEFAULT_CATALOGUE_PREFIX + self.name
        return self.searchable_as

    def get_store_name(self) -> str:
        return self.SECTION + "_" + self.name


class Jenkins(kp.Plugin):
    ITEMCAT_JOB = kp.ItemCategory.USER_BASE + 1
    ITEMCAT_NODE = kp.ItemCategory.USER_BASE + 2

    def __init__(self):
        super().__init__()
        self.jenkins_configs = self._create_jenkins_configs(self.load_settings())
        self.agent_configs = self._create_agent_configs(self.load_settings())
        self.cache = Cache(self.get_package_cache_path(create=True))

    def on_start(self):
        self.cache.clear()
        self.set_actions(self.ITEMCAT_JOB, self._get_job_actions())
        self.set_actions(self.ITEMCAT_NODE, self._get_node_actions())

    def on_catalog(self):
        suggestions = []
        for config in self.jenkins_configs:
            suggestions.append(self.create_item(
                category=kp.ItemCategory.KEYWORD,
                label=config.get_catalogue_name() + ":",
                short_desc="Search and launch '{}' Jenkins jobs...".format(config.name),
                target=JenkinsConfig.DEFAULT_CATALOGUE_PREFIX + config.name,
                args_hint=kp.ItemArgsHint.REQUIRED,
                hit_hint=kp.ItemHitHint.IGNORE
            ))
        for config in self.agent_configs:
            suggestions.append(self.create_item(
                category=kp.ItemCategory.KEYWORD,
                label=config.get_catalogue_name() + ":",
                short_desc="Search '{}' Jenkins nodes...".format(config.name),
                target=AgentConfig.DEFAULT_CATALOGUE_PREFIX + config.name,
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

        if current_target.startswith(JenkinsConfig.DEFAULT_CATALOGUE_PREFIX):
            config = \
                [config for config in self.jenkins_configs if
                 JenkinsConfig.DEFAULT_CATALOGUE_PREFIX + config.name == current_target][
                    0]
            self.set_suggestions(self._get_main_job_suggestions(config), kp.Match.FUZZY, kp.Sort.SCORE_DESC)
        elif len(items_chain) > 1 and first_target.startswith(JenkinsConfig.DEFAULT_CATALOGUE_PREFIX):
            config = \
                [config for config in self.jenkins_configs if
                 JenkinsConfig.DEFAULT_CATALOGUE_PREFIX + config.name == first_target][
                    0]
            self.set_suggestions(self._get_sub_job_suggestions(config, current_item.short_desc()), kp.Match.FUZZY,
                                 kp.Sort.SCORE_DESC)
        elif current_target.startswith(AgentConfig.DEFAULT_CATALOGUE_PREFIX):
            config = \
                [config for config in self.agent_configs if
                 AgentConfig.DEFAULT_CATALOGUE_PREFIX + config.name == current_target][
                    0]
            self.set_suggestions(self._get_main_agent_suggestions(config), kp.Match.FUZZY, kp.Sort.SCORE_DESC)
        elif len(items_chain) > 1 and first_target.startswith(AgentConfig.DEFAULT_CATALOGUE_PREFIX):
            config = \
                [config for config in self.agent_configs if
                 AgentConfig.DEFAULT_CATALOGUE_PREFIX + config.name == first_target][
                    0]
            self.set_suggestions(self._get_nodes_of_label_suggestions(current_item.label(), config),
                                 kp.Match.FUZZY, kp.Sort.SCORE_DESC)

    def on_execute(self, item, action):
        if item.category() in [self.ITEMCAT_JOB, self.ITEMCAT_NODE]:
            if action and action.name() in ["open_url", "copy_url", "open_in_private"]:
                if action.name() == "open_url":
                    kpu.web_browser_command(private_mode=None, new_window=None, url=item.target(), execute=True)
                elif action.name() == "copy_url":
                    kpu.set_clipboard(item.target())
                elif action.name() == "open_in_private":
                    kpu.web_browser_command(private_mode=True, new_window=None, url=item.target(), execute=True)
            else:
                kpu.web_browser_command(private_mode=None, new_window=None, url=item.target(), execute=True)
        else:
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

    def _get_node_actions(self) -> list:
        return self._get_job_actions()

    def _get_job_actions(self) -> list:
        actions = [
            self.create_action(
                name="open_url",
                label="Open",
                short_desc="Open URL",
                data_bag=""
            ),
            self.create_action(
                name="copy_url",
                label="Copy Url",
                short_desc="Copy URL to clipboard",
                data_bag=""
            ),
            self.create_action(
                name="open_in_private",
                label="Open in Private mode",
                short_desc="Open URL in private mode",
                data_bag=""
            )
        ]
        return actions

    def _create_jenkins_configs(self, settings):
        configs = []
        for section in settings.sections():
            if section.lower().startswith(JenkinsConfig.SECTION + "/"):
                section_name = section[len(JenkinsConfig.SECTION) + 1:].strip()
            else:
                continue
            if not len(section_name):
                self.warn("Ignoring empty jenkins section")
                continue
            if not settings.get("jenkins_base_url", section=section, fallback=""):
                self.warn("Section '{}' doesn't have 'jenkins_base_url' defined.".format(section))
                continue
            configs.append(JenkinsConfig(
                section_name,
                settings.get("jenkins_base_url", section=section, fallback="").strip("/"),
                settings.get("search_starts_from", section=section, fallback="/").split(","),
                settings.get("username", section=section, fallback="").strip(),
                settings.get("api_token", section=section, fallback="").strip(),
                settings.get("searchable_as", section=section, fallback="").strip(),
                settings.get_bool("enable_cache", section=section, fallback=True)
            ))
        return configs

    def _create_agent_configs(self, settings):
        configs = []
        for section in settings.sections():
            if section.lower().startswith(AgentConfig.SECTION + "/"):
                section_name = section[len(AgentConfig.SECTION) + 1:].strip()
            else:
                continue
            if not len(section_name):
                self.warn("Ignoring empty agents section")
                continue
            if not settings.get("jenkins_base_url", section=section, fallback=""):
                self.warn("Section '{}' doesn't have 'jenkins_base_url' defined.".format(section))
                continue
            configs.append(AgentConfig(
                section_name,
                settings.get("jenkins_base_url", section=section, fallback="").strip("/"),
                settings.get("username", section=section, fallback="").strip(),
                settings.get("api_token", section=section, fallback="").strip(),
                settings.get("searchable_as", section=section, fallback="").strip()
            ))
        return configs

    def _get_main_agent_suggestions(self, config: AgentConfig):
        url = "{}/computer/api/json?tree=computer[offline,temporarilyOffline,displayName,assignedLabels[name],idle]".format(
            config.base_url)
        nodes = http_get_json(url, config.username, config.api_token)["computer"]
        return self._create_agent_items(nodes, config)

    def _create_agent_items(self, nodes: list, config: AgentConfig):
        suggestions = []
        labels = []
        icon_computer = self.load_icon("res://jenkins/icons/computer.png")
        icon_label = self.load_icon("res://jenkins/icons/label.png")
        for node in nodes:
            labels.extend(_get_labels(node))
            target = "{}/computer/{}".format(config.base_url,
                                             "(master)" if node["displayName"] == "master" else node["displayName"])
            short_desc = "Slave" + ", Idle" if node["idle"] else "Slave"
            short_desc += ", Offline" if node["offline"] else ""
            short_desc += ", TemporarilyOffline" if node["temporarilyOffline"] else ""
            suggestions.append(self.create_item(
                category=self.ITEMCAT_NODE,
                label=node["displayName"],
                short_desc=short_desc,
                target=target,
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.IGNORE,
                icon_handle=icon_computer
            ))
        for label in labels:
            suggestions.append(self.create_item(
                category=self.ITEMCAT_NODE,
                label=label,
                short_desc="Label",
                target="{}/label/{}".format(config.base_url, label),
                args_hint=kp.ItemArgsHint.REQUIRED,
                hit_hint=kp.ItemHitHint.IGNORE,
                icon_handle=icon_label
            ))
        return suggestions

    def _get_nodes_of_label_suggestions(self, label: str, config: AgentConfig):
        suggestions = []
        icon_computer = self.load_icon("res://jenkins/icons/computer.png")
        url = "{}/label/{}/api/json?tree=nodes[nodeName]".format(config.base_url, label)
        nodes = http_get_json(url, config.username, config.api_token)["nodes"]
        for node in nodes:
            target = "{}/computer/{}".format(config.base_url,
                                             "(master)" if node["nodeName"] == "master" else node["nodeName"])
            suggestions.append(self.create_item(
                category=self.ITEMCAT_NODE,
                label=node["nodeName"],
                short_desc="Slave",
                target=target,
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.IGNORE,
                icon_handle=icon_computer
            ))
        return suggestions

    def _get_main_job_suggestions(self, config: JenkinsConfig):
        jobs_response = []
        if self.cache.exists(config.get_store_name() + "_init", config.get_store_name()):
            # loading from local file cache
            jobs_response = self.cache.fetch_object(config.get_store_name() + "_init", config.get_store_name())
        else:
            for folder in config.search_starts_from:
                folder = folder.strip("/").replace("/", "/job/").strip()
                url = "{}/job/{}/api/json?tree=jobs[name,fullName,url]".format(config.base_url, folder)
                if not folder.strip():
                    url = "{}/api/json?tree=jobs[name,fullName,url]".format(config.base_url)
                jobs = http_get_json(url, config.username, config.api_token)["jobs"]
                jobs_response.extend(jobs)
            if config.enable_cache:
                # saving response in local file cache
                self.cache.save_object(config.get_store_name() + "_init", jobs_response, config.get_store_name())
        suggestions = self._create_job_items(jobs_response)
        return suggestions

    def _get_sub_job_suggestions(self, config: JenkinsConfig, folder: str):
        folder = folder.strip("/").replace("/", "/job/").strip()
        cache_name = str(hash(folder))
        if self.cache.exists(cache_name, config.get_store_name()):
            # loading from local file cache
            jobs = self.cache.fetch_object(cache_name, config.get_store_name())
        else:
            url = "{}/job/{}/api/json?tree=jobs[name,fullName,url]".format(config.base_url, folder)
            if not folder.strip():
                url = "{}/api/json?tree=jobs[name,fullName,url]".format(config.base_url)
            jobs = http_get_json(url, config.username, config.api_token)["jobs"]
            if config.enable_cache:
                # saving response in local file cache
                self.cache.save_object(cache_name, jobs, config.get_store_name())
        return self._create_job_items(jobs)

    def _create_job_items(self, jobs: list):
        suggestions = []
        icon_folder = self.load_icon("res://jenkins/icons/folder.png")
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
                    category=self.ITEMCAT_JOB,
                    label=job["name"],
                    short_desc=job["fullName"],
                    target=job["url"],
                    args_hint=kp.ItemArgsHint.REQUIRED,
                    hit_hint=kp.ItemHitHint.IGNORE,
                    icon_handle=icon_folder
                ))
        return suggestions


def http_get_json(url: str, username: str, token: str):
    request = urllib.request.Request(url)
    if username.strip() and token.strip():
        base64string = base64.b64encode((username + ":" + token).encode("ascii"))
        request.add_header("Authorization", "Basic {}".format(base64string.decode("ascii")))
    response = urllib.request.urlopen(request)
    return json.loads(response.read())


def _get_labels(node: dict):
    labels = []
    for assigned_label in node["assignedLabels"]:
        labels.append(assigned_label["name"])
    return labels
