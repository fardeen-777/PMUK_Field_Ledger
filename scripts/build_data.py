import pickle, json, os, re
from parse import extract_hierarchy, parse_month_file

# ---- Known organization-wide renames / formatting noise that should NOT ----
# ---- be counted as a promotion or transfer for the individual. ----
DESIG_SYNONYMS = {
    'Assistant Director & Zonal Manager': 'Assistant Director & Regional Manager',
    'Manager (Admin & Accounts)': 'Manager (Finance & Accounts)',
    'Senior Manager (Admin & Accounts)': 'Senior Manager (Finance & Accounts)',
    'Branch Manager Inc. (ABM- A/C)': 'Branch Manager Inc. (ABM-A/C)',
    'Branch Manager Inc. (ABM- Loan)': 'Branch Manager Inc. (ABM-Loan)',
    'Recovary Officer (BM) (BSRM)': 'Recovery Officer (BM) (BSRM)',
}

def desig_cmp_key(d):
    if d is None:
        return None
    return DESIG_SYNONYMS.get(d, d)

def loc_cmp_key(loc):
    if loc is None:
        return None
    # "X Zone" and "X Region" are the same place under PMUK's renamed org structure
    return re.sub(r'\bzone\b', 'Region', loc, flags=re.I)

# ---- 1. Point this at each month's source file. Add new months at the end. ----
MONTH_FILES = {
    'Jul 25': "fy2526/25-26 Fiscal Year/MF Field Staff Status (July, 25).xlsx",
    'Aug 25': "fy2526/25-26 Fiscal Year/MF Field Staff Status (Aug, 25).xlsx",
    'Sep 25': "fy2526/25-26 Fiscal Year/MF Field Staff Status (Sep, 25).xlsx",
    'Oct 25': "fy2526/25-26 Fiscal Year/MF Field Staff Status (Oct, 25).xlsx",
    'Nov 25': "fy2526/25-26 Fiscal Year/MF Field Staff Status (Nov, 25).xlsx",
    'Dec 25': "fy2526/25-26 Fiscal Year/MF Field Staff Status (Dec, 25).xlsx",
    'Jan 26': "fy2526/25-26 Fiscal Year/MF Field Staff Status (Jan, 26).xlsx",
    'Feb 26': "fy2526/25-26 Fiscal Year/MF Field Staff Status (Feb, 26).xlsx",
    'Mar 26': "fy2526/25-26 Fiscal Year/MF Field Staff Status (Mar, 26).xlsx",
    'Apr 26': "fy2526/25-26 Fiscal Year/MF Field Staff Status (April, 26).xlsx",
    'May 26': "fy2526/25-26 Fiscal Year/MF Field Staff Status (May, 26).xlsx",
}
OUTPUT_PATH = '/home/claude/employee_data.json'

MONTHS = list(MONTH_FILES.keys())

# ---- 2. Parse every month ----
all_month_data = {label: parse_month_file(path) for label, path in MONTH_FILES.items()}

def location_of(rec):
    return rec.get('branch') or rec.get('area') or rec.get('zone')

all_pins = set()
for d in all_month_data.values():
    all_pins.update(d.keys())

master = {}
for pin in all_pins:
    months = {}
    name = None
    for m in MONTHS:
        rec = all_month_data[m].get(pin)
        if rec:
            months[m] = {'designation': rec['designation'], 'location': location_of(rec)}
            name = rec['name']
    master[pin] = {'name': name, 'months': months}

def build_events(entry):
    events = []
    prev = None
    for m in MONTHS:
        cur = entry['months'].get(m)
        if cur is None:
            continue
        if prev is not None:
            promoted = desig_cmp_key(cur['designation']) != desig_cmp_key(prev['designation'])
            transferred = loc_cmp_key(cur['location']) != loc_cmp_key(prev['location'])
            if promoted or transferred:
                events.append({
                    'month': m, 'promoted': promoted, 'transferred': transferred,
                    'from_designation': prev['designation'], 'to_designation': cur['designation'],
                    'from_location': prev['location'], 'to_location': cur['location'],
                })
        prev = cur
    return events

def event_text(ev):
    parts = []
    if ev['promoted']:
        parts.append(f"Promoted to {ev['to_designation']} (from {ev['from_designation']})")
    if ev['transferred']:
        parts.append(f"Transferred to {ev['to_location']} (from {ev['from_location']})")
    return f"{ev['month']}: " + " & ".join(parts)

for pin, entry in master.items():
    events = build_events(entry)
    entry['events'] = events
    entry['summary'] = "\n".join(event_text(e) for e in events) if events else "No change"

# ---- 3. Compress into index-based JSON ----
designations = sorted({rec['designation'] for e in master.values() for rec in e['months'].values()})
locations = sorted({rec['location'] for e in master.values() for rec in e['months'].values() if rec['location']})
desig_idx = {d: i for i, d in enumerate(designations)}
loc_idx = {l: i for i, l in enumerate(locations)}

employees = []
for pin, e in master.items():
    months_arr = []
    for m in MONTHS:
        rec = e['months'].get(m)
        if rec:
            months_arr.append([desig_idx[rec['designation']], loc_idx[rec['location']] if rec['location'] else None])
        else:
            months_arr.append(None)
    events = [{
        'm': ev['month'], 'p': ev['promoted'], 't': ev['transferred'],
        'fd': ev['from_designation'], 'td': ev['to_designation'],
        'fl': ev['from_location'], 'tl': ev['to_location'],
    } for ev in e['events']]
    employees.append({'pin': pin, 'name': e['name'], 'months': months_arr, 'events': events, 'summary': e['summary']})

employees.sort(key=lambda x: (x['name'] or ''))

# ---- 4. Structure map hierarchy: always derived from the LATEST month's file ----
latest_month = MONTHS[-1]
hierarchy = extract_hierarchy(MONTH_FILES[latest_month])

# Parent lookup: branch -> {area, region}, area -> {region}
location_info = {}
for region, areas in hierarchy.items():
    for area, branches in areas.items():
        location_info[area] = {'type': 'area', 'region': region}
        for branch in branches:
            location_info[branch] = {'type': 'branch', 'area': area, 'region': region}
for region in hierarchy.keys():
    location_info[region] = {'type': 'region'}

data = {
    'months': MONTHS,
    'designations': designations,
    'locations': locations,
    'employees': employees,
    'hierarchy': hierarchy,
    'hierarchy_asof': latest_month,
    'location_info': location_info,
}

with open(OUTPUT_PATH, 'w') as f:
    json.dump(data, f, separators=(',', ':'))

print("JSON size (bytes):", os.path.getsize(OUTPUT_PATH))
print("Employees:", len(employees), "Designations:", len(designations), "Locations:", len(locations))
print("Hierarchy as of:", latest_month)

