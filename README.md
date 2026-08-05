# SolviTask

A custom Odoo 17 module for managing a plumbing & heating service business.

## What is this for?

Small field-service companies — plumbers, heating engineers, electricians — run
on scattered information. Jobs arrive by phone and get written on paper, prices
are quoted from memory, nobody records which materials were actually used, and
the invoice is reconstructed days later from half-remembered details. The result
is underbilling, double-booked workers, and no reliable picture of what the
business earned.

SolviTask replaces that with a single record per job. Every request becomes a job
that carries its customer, its price, the plumbers assigned to it, the materials
consumed, the hours spent, and its position in the workflow. Because all of it
lives on one record, the invoice is not reconstructed — it is generated from what
was actually logged.

The module answers the questions a service business asks daily:

- What work is booked, and what state is each job in right now?
- Who is assigned to what, and is that person even available?
- What did this job actually cost once materials and labor are counted?
- What do we charge for this kind of work, and how many people does it need?
- What goes on the customer's invoice?

**Business scope.** This covers operations: intake, pricing, scheduling,
assignment, execution, and invoicing. Accounting, payroll, and stock control are
deliberately out of scope — the module produces an invoice *document*, not
accounting entries.

**Technical scope.** Built for Odoo 17 Community. Depends on `base` and `web`
only, so installing it adds nothing to the Apps menu but itself.

---

## Table of contents

- [Concepts](#concepts)
- [Business operations](#business-operations)
- [Data model](#data-model)
- [Business rules](#business-rules)
- [Usage](#usage)
- [Installation](#installation)
- [Importing starter data](#importing-starter-data)
- [Roles and access](#roles-and-access)
- [Project layout](#project-layout)
- [Known issues / TODO](#known-issues--todo)

---

## Concepts

Two ideas are worth understanding before reading the code.

**Service vs. Job.** A *service* is a catalog entry — a kind of work you offer,
with a price and a typical crew size. A *job* is one real occurrence of that work,
for one customer, on one date. One service is referenced by many jobs. A job can
also exist with no service at all: that is a **custom request**, where the
customer describes a problem that isn't in the catalog.

**Stages are data, not code.** The job pipeline is a separate model
(`solvitask.job.stage`) rather than a hard-coded selection field. Stages can be
renamed, reordered, added, or removed from the UI without touching Python. Two
boolean flags on each stage drive the business logic:

| Flag | Meaning |
|---|---|
| `is_started` | Work begins here. Entering this stage enforces the start rules. |
| `is_done` | Work is finished. The invoice button appears from here on. |

---

## Business operations

What the module actually does, grouped by the business function it serves.

### 1. Service catalog management

Define what the company sells. Each service carries a unit price, a description,
the number of plumbers it normally requires, and the tools recommended for it.
The catalog is the single source of truth for pricing — change a price once and
every future job quotes the new figure, while jobs already priced keep what they
were quoted.

### 2. Customer management

Maintain customer records with contact details and address. Each customer's job
history is visible on their record, along with a count of jobs, giving an
immediate view of the relationship.

### 3. Workforce management

Register plumbers with their hourly rate, payment method (cash or bank
transfer), and skills — the services each is qualified to perform. An
availability flag marks who can currently be assigned; the system refuses to
assign anyone marked unavailable.

### 4. Inventory catalogs

Maintain reference lists of tools and materials. Materials carry a unit (kg,
meter, liter, piece) and a unit price, which is what makes automatic material
costing possible.

### 5. Job intake

Register incoming work as either a **listed service** chosen from the catalog,
or a **custom request** where the customer describes a problem that isn't
offered as a standard service. A priority level (emergency, high, normal, low)
records urgency, and a photo of the problem can be attached.

### 6. Pricing and quotation

Listed services inherit their price from the catalog automatically; custom jobs
are priced manually. The quoted price remains editable per job, so an unusually
difficult instance of a standard service can be repriced without disturbing the
catalog.

### 7. Scheduling and assignment

Set an appointment date — which advances the job to *Scheduled* automatically —
and assign one or more plumbers. The service's required crew size is displayed
so the scheduler knows how many people to send, and availability is validated at
the moment of assignment.

### 8. Job execution tracking

Move jobs through the pipeline by dragging cards on a kanban board or clicking
the status bar. During the work, plumbers record materials consumed (with
quantities), hours spent, and written notes on what was found and fixed.

### 9. Cost calculation

Three figures are computed continuously and never typed by hand:

- **Material cost** — the sum of every material line, each line being quantity
  multiplied by the material's unit price.
- **Labor cost** — hours multiplied by hourly rate, applied to custom jobs only;
  listed services are covered by their catalog price.
- **Total price** — quoted price plus labor plus materials.

### 10. Workflow control

The pipeline is configurable data rather than fixed code. Stages can be renamed,
reordered, added, or folded from the UI. Two flags per stage determine where the
business rules apply: which stage counts as "work has started" and which counts
as "work is finished".

### 11. Invoicing

Generate a PDF invoice from a completed job. It itemizes the materials used,
shows the price breakdown, and is saved as an attachment on the job record so
there is a permanent copy of what was billed. It can also be printed at any time
from the Print menu.

### 12. Operational oversight

Filter and group jobs by stage, assigned plumber, priority, or type (listed
versus custom); identify unassigned work and emergencies; and read job totals as
a summed column in the list view.

---

## Data model

| Model | Purpose |
|---|---|
| `solvitask.job` | Central model. One customer request / job. |
| `solvitask.job.material` | Line item: one material used on one job, with quantity. |
| `solvitask.job.stage` | Pipeline stages (kanban columns). |
| `solvitask.customer` | Customer contact details. |
| `solvitask.worker` | Plumber, with hourly rate, availability, and skills. |
| `solvitask.service` | Service catalog: price and crew size per kind of work. |
| `solvitask.tool` | Tool catalog. |
| `solvitask.material` | Material catalog: unit and unit price. |

### Relationships

```
customer  1 ──< job >── 1  service
worker    N ──< job              (many-to-many: a job can need several plumbers)
stage     1 ──< job
job       1 ──< job.material >── 1  material
worker    N ──< service          (skills)
service   N ──< tool             (recommended tools)
job       N ──< tool             (tools required on site)
```

### Pricing

Three stored computed fields build the total. All of them recalculate
automatically — nothing is typed in by hand except `initial_price` and
`hours_worked`.

```
initial_price   copied from service.unit_price when a service is chosen,
                then editable (a custom job has no service, so it is typed in)

labor_cost      custom jobs:  sum over assigned workers of (hourly_rate × hours_worked)
                listed jobs:  always 0 — the catalog price already covers labor

material_cost   sum of every material line's subtotal
                (a line's subtotal = quantity × unit_price)

total_price     initial_price + labor_cost + material_cost
```

---

## Business rules

Enforced in `models/job.py`. All of them are `@api.constrains`, meaning they run
on **every** save — through the form, the kanban board, a data import, or code —
not just when a button is clicked.

1. **A job cannot start without an assigned worker.**
   Entering any stage flagged `is_started` requires at least one worker in
   `worker_ids`.

2. **A job cannot start with a total price of 0.**
   Forces a price to be quoted before work begins. Relevant mostly for custom
   jobs, which have no catalog price to inherit.

3. **Unavailable workers cannot be assigned.**
   Assigning a worker whose `available` flag is off is rejected, and the error
   message names them.

4. **A job is either a listed service or a custom request, never both and never
   neither.** Ticking *Custom request* clears the service field; saving with both
   set, or with neither, is rejected.

5. **A service requires at least one worker.** `worker_count` must be ≥ 1.

Because rules 1 and 2 hook the write to `stage_id`, they apply equally to
dragging a card on the kanban board and clicking the status bar in the form.

### Convenience behaviour

- Setting a scheduled date moves the job into the *Scheduled* stage automatically.
- Ticking *Custom request* clears the selected service.
- Choosing a service prefills the initial price from the catalog.

---

## Usage

### Daily flow

1. **Request arrives.** Create a job, pick the customer, and either choose a
   service or tick *Custom request* and describe the problem. Priority defaults
   to Normal.
2. **Price it.** For a listed service the initial price fills in from the
   catalog; for a custom job, type it in.
3. **Schedule and assign.** Set the scheduled date (the job moves to *Scheduled*)
   and add one or more plumbers. The service's *Workers Required* field shows how
   many the job normally needs.
4. **Work.** Plumbers move the job through *In Progress* / *Waiting for Parts*,
   add material lines, hours, and work notes.
5. **Complete.** Drag to *Completed*. The **Generate Invoice** button appears.
6. **Invoice.** Click it — a PDF is rendered, saved as an attachment on the job,
   and downloaded. It is also available any time under **Print → Job Invoice**.

### The kanban board

Jobs open on a kanban view grouped by stage. Drag cards between columns to move
jobs through the pipeline; the business rules above still apply, and an invalid
move is rejected and the card snaps back. Columns come from
**SolviTask → Configuration → Job Stages**, where you can rename them, drag to
reorder, fold them, or set the `is_started` / `is_done` flags.

---

## Installation

```bash
# 1. Put the module in your addons path
cp -r solvitask /path/to/odoo/addons/

# 2. Restart Odoo with the addons path
./odoo-bin -d <database> --addons-path=/path/to/odoo/addons

# 3. Update the apps list, then install "SolviTask" from the Apps menu
```

To apply changes after editing the code:

```bash
./odoo-bin -d <database> -u solvitask
```

Generating invoice PDFs requires `wkhtmltopdf` to be installed on the server.

---

## Importing starter data

CSV files with Albanian-language data are provided for a quick start. Import them
in this order, via **⚙️ → Import records** on each list view:

| File | Import into | Columns |
|---|---|---|
| `vegla_hidraulike.csv` | Tools | `name`, `description` |
| `materiale_hidraulike.csv` | Materials | `name`, `unit`, `unit_price` |
| `sherbime_hidraulike.csv` | Services | `name`, `unit_price`, `worker_count`, `description` |

The `unit` column uses the stored selection values (`kg`, `m`, `l`, `unit`). If
the importer objects, enable **"Use the technical column names"** in the import
dialog. All files are UTF-8.

---

## Roles and access

Three security groups are defined in `security/groups.xml`, chained with
`implied_ids` so each one inherits the level below:

| Group | Sees | Can do |
|---|---|---|
| **Worker** | Only jobs they are assigned to | Update job progress, add materials, hours, notes |
| **Manager** | All jobs, customers, workers | Everything a worker can, plus assign, price, and configure |
| **Administrator** | Everything | Full control |

Row-level filtering is done with `ir.rule` records in
`security/security_rules.xml`; column-level permissions are in
`security/ir.model.access.csv`. Managers are deliberately **not** members of
Odoo's `base.group_system`, so they run the business without access to technical
system settings.

---

## Project layout

```
solvitask/
├── __manifest__.py              module metadata and data file list
├── models/
│   ├── job.py                   job + material line, all business rules
│   ├── job_stage.py             pipeline stages
│   ├── customer.py              customers
│   ├── worker.py                plumbers
│   ├── service.py               service catalog
│   ├── tool.py                  tool catalog
│   └── material.py              material catalog
├── views/                       form / tree / kanban / search views and menus
├── security/
│   ├── groups.xml               the three roles
│   ├── security_rules.xml       row-level record rules
│   └── ir.model.access.csv      model-level permissions
├── data/
│   └── job_stage_data.xml       default pipeline stages
└── report/
    └── job_invoice_report.xml   QWeb invoice template + report action
```

---

## Known issues / TODO

Current gaps, in rough priority order:

- **`worker.job_ids` does not mirror `job.worker_ids`.** Both are declared as
  `Many2many` without a shared `relation` name, so Odoo generates *two separate*
  link tables and the two sides never see each other's data. They need to point
  at the same relation table to work as one relationship.
- **The worker approval workflow was removed** (`user_id`, `state`,
  `action_approve`), but `security/security_rules.xml`, `views/worker_view.xml`,
  and the companion website module still reference those fields. Either restore
  them or update the referencing files.
- **Record rules still reference `worker_id`**, which was renamed to `worker_ids`.
  The domains need updating to match.
- **Labor cost multiplies every worker by the same `hours_worked`.** Two plumbers
  on a 3-hour job bill 3 hours each. If crew members work different hours, this
  needs a per-worker line model like the material lines.
- **The scheduled-date onchange matches the stage by the literal name
  `"Scheduled"`.** Renaming or translating that stage silently breaks it; a
  boolean flag on the stage model would be more robust.
- Payment tracking, worker payouts, and financial reports are not implemented.

---

## License

Licensed under the **GNU Lesser General Public License v3.0 (LGPL-3.0)**.

Odoo Community Edition is itself LGPL-3.0. Because this module imports from and
runs inside Odoo, it is a derivative work, and its license must be LGPL-3.0 or
compatible — a permissive license such as MIT is not an option here. LGPL-3.0
matches Odoo Community, is the license Odoo recommends for Community modules, and
permits commercial use and private modification.

To apply it: add the full license text as a `LICENSE` file (available from
<https://www.gnu.org/licenses/lgpl-3.0.txt>) and declare it in `__manifest__.py`:

```python
'license': 'LGPL-3',
```
