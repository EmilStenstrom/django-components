import re
import textwrap
from collections import defaultdict
from urllib import request


def get_supported_versions(url):
    with request.urlopen(url) as response:
        response_content = response.read()

    content = response_content.decode("utf-8")

    def parse_supported_versions(content):
        def cut_by_content(content, cut_from, cut_to):
            return content.split(cut_from)[1].split(cut_to)[0]

        def keys_from_content(content):
            return re.findall(r"<td>(.*?)</td>", content)

        content = cut_by_content(
            content,
            '<span id="what-python-version-can-i-use-with-django">',
            "</table>",
        )
        content = cut_by_content(content, '<tbody valign="top">', "</tbody>")

        versions = keys_from_content(content)
        version_dict = dict(zip(versions[::2], versions[1::2]))

        django_to_python = {
            version_to_tuple(python_version): [
                version_to_tuple(version_string)
                for version_string in re.findall(
                    r"(?<!\.)\d+\.\d+(?!\.)", django_versions
                )
            ]
            for python_version, django_versions in version_dict.items()
        }
        return django_to_python

    return parse_supported_versions(content)


def get_latest_version(url):
    with request.urlopen(url) as response:
        response_content = response.read()

    content = response_content.decode("utf-8")
    version_string = re.findall(
        r"The latest official version is (\d+\.\d)", content
    )[0]
    return version_to_tuple(version_string)


def version_to_tuple(version_string):
    return tuple(int(num) for num in version_string.split("."))


def build_python_to_django(django_to_python, latest_version):
    python_to_django = defaultdict(list)
    for django_version, python_versions in django_to_python.items():
        for python_version in python_versions:
            if django_version <= latest_version:
                python_to_django[python_version].append(django_version)

    python_to_django = dict(python_to_django)
    return python_to_django


def env_format(version_tuple, divider=""):
    return divider.join(str(num) for num in version_tuple)


def build_tox_envlist(python_to_django):
    lines = [
        (
            env_format(python_version),
            ",".join(env_format(version) for version in django_versions),
        )
        for python_version, django_versions in python_to_django.items()
    ]
    lines = [f"py{a}-django{{{b}}}" for a, b in lines]
    version_lines = "\n".join([version for version in lines])
    return "envlist = \n" + textwrap.indent(version_lines, prefix="  ")


def build_gh_actions_envlist(python_to_django):
    lines = [
        (
            env_format(python_version, divider="."),
            env_format(python_version),
            ",".join(env_format(version) for version in django_versions),
        )
        for python_version, django_versions in python_to_django.items()
    ]
    lines = [f"{a}: py{b}-django{{{c}}}" for a, b, c in lines]
    version_lines = "\n".join([version for version in lines])
    return "python = \n" + textwrap.indent(version_lines, prefix="  ")


def build_deps_envlist(python_to_django):
    all_django_versions = set()
    for django_versions in python_to_django.values():
        for django_version in django_versions:
            all_django_versions.add(django_version)

    lines = [
        (
            env_format(django_version),
            env_format(django_version, divider="."),
            env_format(
                (django_version[0], django_version[1] + 1), divider="."
            ),
        )
        for django_version in all_django_versions
    ]
    lines = [f"django{a}: Django>={b},<{c}" for a, b, c in lines]
    return "deps = \n" + textwrap.indent("\n".join(lines), prefix="  ")


def build_pypi_classifiers(python_to_django):
    classifiers = []

    all_python_versions = python_to_django.keys()
    for python_version in all_python_versions:
        classifiers.append(
            f"Programming Language :: Python :: {env_format(python_version, divider='.')}"
        )

    all_django_versions = set()
    for django_versions in python_to_django.values():
        for django_version in django_versions:
            all_django_versions.add(django_version)

    classifiers.append("...")

    for django_version in all_django_versions:
        classifiers.append(
            f"Programming Language :: Django :: {env_format(django_version, divider='.')}"
        )

    return "classifiers=[\n" + textwrap.indent(
        "\n".join(classifiers), prefix="  "
    )


def build_readme(python_to_django):
    print(
        textwrap.dedent(
            """\
                | Python version | Django version           |
                |----------------|--------------------------|
            """.rstrip()
        )
    )
    lines = [
        (
            env_format(python_version, divider="."),
            ", ".join(
                env_format(version, divider=".") for version in django_versions
            ),
        )
        for python_version, django_versions in python_to_django.items()
    ]
    lines = [f"| {a: <14} | {b: <24} |" for a, b in lines]
    version_lines = "\n".join([version for version in lines])
    return version_lines


def main():
    django_to_python = get_supported_versions(
        "https://docs.djangoproject.com/en/dev/faq/install/"
    )
    latest_version = get_latest_version(
        "https://www.djangoproject.com/download/"
    )

    python_to_django = build_python_to_django(django_to_python, latest_version)

    tox_envlist = build_tox_envlist(python_to_django)
    print("Add this to tox.ini:\n")
    print("[tox]")
    print(tox_envlist)
    print()

    gh_actions_envlist = build_gh_actions_envlist(python_to_django)
    print("[gh-actions]")
    print(gh_actions_envlist)
    print()

    deps_envlist = build_deps_envlist(python_to_django)
    print("[testenv]")
    print(deps_envlist)
    print()
    print()

    print("Add this to setup.py:\n")
    pypi_classifiers = build_pypi_classifiers(python_to_django)
    print(pypi_classifiers)
    print()
    print()

    print("Add this to README:\n")
    readme = build_readme(python_to_django)
    print(readme)
    print()


if __name__ == "__main__":
    main()
