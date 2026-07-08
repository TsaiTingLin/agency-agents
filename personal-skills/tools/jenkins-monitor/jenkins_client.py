import os
import re
import requests
from requests.auth import HTTPBasicAuth


class JenkinsClient:
    def __init__(self):
        self.base_url = os.environ["JENKINS_URL"].rstrip("/")
        self.auth = HTTPBasicAuth(os.environ["JENKINS_USER"], os.environ["JENKINS_TOKEN"])

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def list_jobs(self) -> list[str]:
        r = requests.get(self._url("/api/json?tree=jobs[name]"), auth=self.auth, verify=False)
        r.raise_for_status()
        return [j["name"] for j in r.json().get("jobs", [])]

    def get_job_info(self, job: str) -> dict:
        r = requests.get(self._url(f"/job/{job}/api/json"), auth=self.auth, verify=False)
        r.raise_for_status()
        return r.json()

    def get_job_parameters(self, job: str) -> list[dict]:
        info = self.get_job_info(job)
        for action in info.get("actions", []):
            if action.get("_class") == "hudson.model.ParametersDefinitionProperty":
                return action.get("parameterDefinitions", [])
        return []

    def trigger_build(self, job: str, branch: str, product_flavor: str | None = None) -> int:
        """Trigger build and return queue item number."""
        params = self.get_job_parameters(job)
        branch_param = next(
            (p["name"] for p in params if "branch" in p["name"].lower()),
            "BRANCH_NAME",
        )
        build_params = {branch_param: branch}
        if product_flavor is not None:
            build_params["ProductFlavor"] = product_flavor
        r = requests.post(
            self._url(f"/job/{job}/buildWithParameters"),
            auth=self.auth,
            params=build_params,
            verify=False,
        )
        r.raise_for_status()
        location = r.headers.get("Location", "")
        queue_num = int(location.rstrip("/").split("/")[-1]) if location else -1
        return queue_num

    def get_queue_item(self, queue_num: int) -> dict:
        r = requests.get(
            self._url(f"/queue/item/{queue_num}/api/json"),
            auth=self.auth,
            verify=False,
        )
        r.raise_for_status()
        return r.json()

    def get_build_info(self, job: str, build_number: int | str = "lastBuild") -> dict:
        r = requests.get(
            self._url(f"/job/{job}/{build_number}/api/json"),
            auth=self.auth,
            verify=False,
        )
        r.raise_for_status()
        return r.json()

    def get_build_log(self, job: str, build_number: int | str = "lastBuild", max_lines: int = 200) -> str:
        r = requests.get(
            self._url(f"/job/{job}/{build_number}/consoleText"),
            auth=self.auth,
            verify=False,
        )
        r.raise_for_status()
        lines = r.text.splitlines()
        if len(lines) > max_lines:
            lines = ["... (truncated) ..."] + lines[-max_lines:]
        return "\n".join(lines)

    def rename_job(self, job: str, new_name: str) -> None:
        """Rename a Jenkins job."""
        r = requests.post(
            self._url(f"/job/{job}/doRename"),
            auth=self.auth,
            params={"newName": new_name},
            verify=False,
        )
        r.raise_for_status()

    def update_job_parameter(self, job: str, param_name: str, value: str) -> None:
        """Update a job parameter's default value (String) or first choice (Choice)."""
        r = requests.get(self._url(f"/job/{job}/config.xml"), auth=self.auth, verify=False)
        r.raise_for_status()
        xml = r.text

        # StringParameterDefinition: replace <defaultValue>
        str_pat = re.compile(
            r"(<hudson\.model\.StringParameterDefinition>.*?<name>"
            + re.escape(param_name)
            + r"</name>.*?<defaultValue>)(.*?)(</defaultValue>)",
            re.DOTALL,
        )
        if str_pat.search(xml):
            updated = str_pat.sub(lambda m: m.group(1) + value + m.group(3), xml)
        else:
            # ChoiceParameterDefinition: reorder so value is first
            block_pat = re.compile(
                r"<hudson\.model\.ChoiceParameterDefinition>.*?<name>"
                + re.escape(param_name)
                + r"</name>.*?</hudson\.model\.ChoiceParameterDefinition>",
                re.DOTALL,
            )
            block_match = block_pat.search(xml)
            if not block_match:
                raise ValueError(f"Parameter '{param_name}' not found in job '{job}'")
            block = block_match.group(0)
            choices = re.findall(r"<string>(.*?)</string>", block)
            if value not in choices:
                raise ValueError(f"'{value}' is not valid. Options: {choices}")
            choices.remove(value)
            choices.insert(0, value)
            idx = [0]

            def replace_in_order(m: re.Match) -> str:
                result = f"<string>{choices[idx[0]]}</string>"
                idx[0] += 1
                return result

            updated_block = re.sub(r"<string>.*?</string>", replace_in_order, block)
            updated = xml.replace(block, updated_block)

        resp = requests.post(
            self._url(f"/job/{job}/config.xml"),
            auth=self.auth,
            data=updated.encode("utf-8"),
            headers={"Content-Type": "application/xml"},
            verify=False,
        )
        resp.raise_for_status()

    def get_test_report(self, job: str, build_number: int | str = "lastBuild") -> dict | None:
        try:
            r = requests.get(
                self._url(f"/job/{job}/{build_number}/testReport/api/json"),
                auth=self.auth,
                verify=False,
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except Exception:
            return None
