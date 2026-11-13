"""Project a pinned Light GeoSite DAT into one server RU category.

GeoSite protobuf layout: v2fly/v2ray-core/app/router/routercommon/common.proto.
The retained Domain submessages are copied byte-for-byte, including their type.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT, FULL = 2, 3
DOMAIN = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
REQUIRED_ROOTS = {"ru", "su", "xn--p1ai", "by", "kz", "xn--90ais", "xn--80ao21a"}


def varint(value):
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def read_varint(data, pos):
    value = 0
    for shift in range(0, 70, 7):
        if pos == len(data):
            raise ValueError("truncated protobuf varint")
        byte = data[pos]
        pos += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, pos
    raise ValueError("oversized protobuf varint")


def fields(data):
    pos = 0
    while pos < len(data):
        key, pos = read_varint(data, pos)
        field, wire = divmod(key, 8)
        if not field:
            raise ValueError("invalid protobuf field 0")
        if wire == 0:
            value, pos = read_varint(data, pos)
        elif wire == 2:
            size, pos = read_varint(data, pos)
            end = pos + size
            if end > len(data):
                raise ValueError("truncated protobuf field")
            value, pos = data[pos:end], end
        else:
            raise ValueError(f"unexpected protobuf wire type {wire}")
        yield field, value


def message(field, value):
    return varint(field * 8 + 2) + varint(len(value)) + value


def ancestors(name):
    while "." in name:
        name = name.split(".", 1)[1]
        yield name


def valid_name(name):
    return len(name) <= 253 and all(DOMAIN.fullmatch(label) for label in name.split("."))


def read_ru(data):
    codes, rules = set(), {}
    for field, site in fields(data):
        if field != 1 or not isinstance(site, bytes):
            raise ValueError("unexpected GeoSiteList field")
        entries = list(fields(site))
        names = [value for key, value in entries if key == 1]
        if len(names) != 1 or not isinstance(names[0], bytes) or not names[0]:
            raise ValueError("missing or duplicate category name")
        code = names[0].decode("ascii")
        if code in codes:
            raise ValueError(f"duplicate category {code}")
        codes.add(code)
        if code != "RU":
            continue
        for field, payload in entries:
            if field == 1:
                continue
            if field != 2 or not isinstance(payload, bytes):
                raise ValueError("unexpected RU category field")
            parts = list(fields(payload))
            domain = dict(parts)
            if len(parts) != 2 or set(domain) != {1, 2}:
                raise ValueError("RU domain must have a type and a name, without attributes")
            typ, value = domain[1], domain[2]
            if typ not in (ROOT, FULL) or not isinstance(value, bytes):
                raise ValueError("RU domain must be a suffix or an exact hostname")
            name = value.decode("ascii")
            if not valid_name(name) or (typ, name) in rules:
                raise ValueError(f"invalid or duplicate RU rule {name!r}")
            rules[typ, name] = payload
    if "RU" not in codes or not rules:
        raise ValueError("missing or empty RU category")
    return codes, rules


def excluded(typ, name, deny):
    return (name in deny or any(a in deny for a in ancestors(name)) or
            (typ == ROOT and any(d.endswith("." + name) for d in deny)))


def encode(rules):
    body = message(1, b"RU") + b"".join(message(2, payload)
                                         for _, payload in sorted(rules.items(), key=lambda item: (item[0][1], item[0][0])))
    return message(1, body)


def project(source, deny, retain):
    _, incoming = read_ru(source)
    output = {key: payload for key, payload in incoming.items() if not excluded(*key, deny)}
    for name in retain:
        if excluded(ROOT, name, deny):
            raise ValueError(f"retained server rule conflicts with exclusions: {name}")
        output.setdefault((ROOT, name), b"\x08\x02" + message(2, name.encode("ascii")))

    suffixes = {name for typ, name in output if typ == ROOT}
    output = {key: payload for key, payload in output.items()
              if not any(a in suffixes for a in ancestors(key[1]))
              and not (key[0] == FULL and key[1] in suffixes)}
    result = encode(output)
    categories, rules = read_ru(result)
    if categories != {"RU"} or rules != output or not REQUIRED_ROOTS <= suffixes:
        raise ValueError("server DAT failed RU-only validation")
    return result, incoming, output


def policy_list(path):
    items = [line.split("#", 1)[0].strip() for line in path.read_text().splitlines()]
    names = set(filter(None, items))
    if not names or any(not valid_name(name) for name in names):
        raise ValueError(f"invalid policy list: {path}")
    return names


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--policy-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "data")
    args = parser.parse_args()
    config = json.loads((args.policy_dir / "light-source.json").read_text())
    source = args.source.read_bytes()
    if digest(source) != config["sha256"]:
        raise SystemExit("Source DAT SHA-256 does not match the pinned Light release")
    deny = policy_list(args.policy_dir / "exclude-server-suffixes.txt")
    retain = policy_list(args.policy_dir / "retain-server-suffixes.txt")
    result, incoming, output = project(source, deny, retain)
    result_sha = digest(result)
    if result_sha != config["server_sha256"]:
        raise SystemExit(f"Projected Server DAT SHA-256 does not match the reviewed build: {result_sha}")
    args.destination.mkdir(parents=True, exist_ok=True)
    (args.destination / "geosite_RU.dat").write_bytes(result)
    (args.destination / "geosite_RU.dat.sha256sum").write_text(f"{result_sha}  geosite_RU.dat\n")
    (args.destination / "geosite_RU_categories.txt").write_text("RU\n")
    print(f'Light {config["tag"]}: {len(incoming)} RU rules')
    print(f'Server RU: {len(output)} rules, {sum(t == FULL for t, _ in output)} exact hostnames')
    print(f'Excluded from Light RU: {sum(excluded(*key, deny) for key in incoming)} rules')
    print(f'Additional Server suffixes: {sum(key not in incoming for key in output)}')
    print(f'Server DAT SHA-256: {result_sha}')


if __name__ == "__main__":
    main()
