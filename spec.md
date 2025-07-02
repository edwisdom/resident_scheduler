# Emergency Department Resident Scheduling System

## Task
The task is to schedule 60 residents for their shifts in the emergency department, with the goal of hitting a certain number of hours per month. There are three classes (or years), each with 20 residents. PGY-1, PGY-2, PGY-3. For the most part, their shifts are separate, although there are some shifts which may have some crossover-coverage, which I'll elaborate on below.

Each day, there are a certain number of mandatory shifts that must be staffed by one resident. Each resident should only be scheduled for one shift per day. However, there are duty hour constraints that the scheduler must abide by.

## Duty Hours
For the purposes of duty hours, the work week spans from Monday to Sunday.
1. Residents may not work longer than 12 continuous scheduled hours.
2. There must be at least one equivalent period of continuous time off between scheduled work period. In other words, if a resident works a shift that is X hours long, they should have at least X hours off before their next shift.
3. A resident must not work more than 60 scheduled hours per week.
4. Residents must have a minimum of one day (24-hour period) free per seven-day period.

## Shift Details
Below each day is a list of mandatory shifts that must be staffed. There are two hospitals (hospital L and hospital W) that have their individual shifts. Shifts are denoted by two letters followed by a number.

The first letter is either L or W (denoting the hospital).
The second letter denotes the team in the emergency department.
- R: Red team (staffed by PGY-3's)
- G: Green team (staffed by PGY-2's)
- I: "Intern" team (staffed by PGY-1's)
- E: Eval team (staffed by any resident, but prefer PGY-1)
- B: Blue team (staffed by one PGY-1 at all times, but can add on a PGY-2 or PGY-3 to meet hours goal. Note: There is no Blue team at hospital W)
- P: Pediatrics (staffed by PGY-1 preferably, but can add PGY-2 or PGY-3 if needed). These shifts are always 10 hours long regardless of PGY year.

The number denotes the time at which the shift starts. The only AM shifts are 7, 9, and 11. For intern shifts, d starts at 7A, and n starts at 7P.

PGY-1 shifts are all 12 hours long. PGY-2 and PGY-3 shifts are all 10 hours long. If a PGY-2 or PGY-3 is scheduled for Eval, their shift lasts 10 hours instead of 12 for interns. Note that on Wednesdays, residents cannot be scheduled for a 7AM shift. LIdw and LB11w are 2PM to 7PM and 2PM to 11PM, respectively. These are both intern shifts.

Shifts that are in parentheses are optional shifts, but should be scheduled for a resident to get them as close as possible to their hour goal.

## Weekly Shift Schedule
| Day | Monday | Tuesday | Wednesday | Thursday | Friday | Saturday | Sunday |
|-----|--------|---------|-----------|----------|--------|----------|--------|
| | LR7 | LR7 | | LR7 | LR7 | LR7 | LR7 |
| | LR2 | LR2 | LR2 | LR2 | LR2 | LR2 | LR2 |
| | LR4 | LR4 | LR4 | LR4 | LR4 | | |
| | LRn | LRn | LRn | LRn | LRn | LRn | LRn |
| | LG7 | LG7 | | LG7 | LG7 | LG7 | LG7 |
| | LG1 | LG1 | LG1 | LG1 | LG1 | LG2 | LG2 |
| | LG4 | LG4 | LG4 | LG4 | LG4 | - | - |
| | LGn | LGn | LGn | LGn | LGn | LGn | LGn |
| | LId | LId | LIdw | LId | LId | LId | LId |
| | LIn | LIn | LIn | LIn | LIn | LIn | LIn |
| | LB11 | LB11 | LB11w | LB11 | LB11 | - | - |
| | LE11 | LE11 | (LE2) | (LE11) | (LE11) | (LE9) | (LE9) |
| | LP7 | LP7 | | LP7 | LP7 | LP7 | LP7 |
| | LP1 | LP1 | LP1 | LP1 | LP1 | LP2 | LP2 |
| | (LP4) | | | (LP4) | (LP4) | | |
| | LPn | LPn | LPn | LPn | LPn | LPn | LPn |
| | WR7 | WR7 | | WR7 | WR7 | WR7 | WR7 |
| | WR1 | WR1 | WR1 | WR1 | WR1 | WR1 | WR1 |
| | (WR4) | (WR4) | (WR4) | (WR4) | (WR4) | | |
| | WRn | WRn | WRn | WRn | WRn | WRn | WRn |
| | WG7 | WG7 | | WG7 | WG7 | WG7 | WG7 |
| | WG1 | WG1 | WG1 | WG1 | WG1 | WG1 | WG1 |
| | WG4 | WG4 | WG4 | WG4 | WG4 | - | - |
| | LGn | LGn | LGn | LGn | LGn | LGn | LGn |
| | WId | WId | WIdw | WId | WId | WId | WId |
| | (WIn) | (WIn) | (WIn) | (WIn) | (WIn) | (WIn) | (WIn) |
| | WE9 | (WE9) | (WE2) | WE9 | (WE9) | WE9 | WE9 |

## Hour Goals
A block is a period of 4 weeks. Each PGY class has different "hours per block goals." This is a soft goal, as residents can do more or less hours in the next block depending on if they are above or below goal. However, the scheduler should try to get as close as possible to the target. Highlighted PGY-3's are chief residents, and their hours/block goals are slightly less.

On my Excel sheet, there is a column that tells me a resident's true hours/block goal. This takes into account the number of hours they owe or overworked from the previous shift. Ideally I would be able to enter this number into the table 2 sections down and the program can adapt the schedule accordingly.

## Other Constraints
1. If a resident is scheduled to work a night shift, they should always be scheduled for 3 or 4 nights in a row. When they are, the shifts should alternate between the two hospitals (so WRn, LRn, WRn, LRn).
2. The alternating between hospitals rule should generally apply if residents are scheduled to work multiple days in a row.
3. In general, the schedule should try to not disrupt the circadian rhythm of the residents as much as possible. Thus, it should try to have 7AM shifts grouped with 1PM or 2PM shifts instead of flip-flopping between 7AM and 4PM too quickly. It would be ideal for a resident to be slowly transitioned into nights and go from 7AM shifts → 1PM or 4PM → Overnight shift, and then a day off → afternoon shifts → 7AM shifts. This is not a hard rule, but should be preferred.

## Residents
One thing that the scheduler should take into account is whether or not a resident is on an "ED block." This means that they are rotating in the ED and thus is eligible to be scheduled for shifts. In any given block, there are a varying number of residents who are on "off-service" or on vacation. These residents are not eligible to be scheduled for shifts. My initial plan was to have an Excel table like the one below with a column denoting the type of block they are in. If a resident is off-service or on vacation, the scheduler should essentially ignore them.

Special note: PGY-1 and PGY-2 classes can be scheduled for a "Peds" block, in which case they should be the only pool from which the scheduler selects residents for the P shifts. However, PGY-3 residents can also be selected at random if there are not enough residents to fill all the required P shifts. PGY-1's on a Peds block have a slightly different hours/block goal.

There is also a column for "Requests" which are days off that a resident wants during this block. The scheduler should try to accommodate them as much as possible, but not to the point of violating any duty hours. I put in random days off in this column for now.

### PGY-3 Residents
| Resident | PGY | Service | Hours/Block Goal | Requests |
|----------|-----|---------|-----------------|----------|
| HA | 3 | ED | 170 | |
| JA | 3 | Off-Service | 170 | |
| SA | 3 | ED | 150 | |
| AB | 3 | Off-Service | 170 | |
| JC | 3 | ED | 170 | |
| PG | 3 | ED | 150 | |
| SK | 3 | Off-Service | 170 | 7/8, 7/9 |
| NK | 3 | ED | 170 | |
| CK | 3 | Off-Service | 170 | 8/2 |
| BM | 3 | Off-Service | 170 | 7/4 |
| RP | 3 | Off-Service | 170 | |
| DS | 3 | Vacation | 170 | |
| CS | 3 | ED | 170 | |
| TT | 3 | ED | 150 | |
| JT | 3 | Peds | 170 | 7/25, 7/26, 7/27 |
| AVa | 3 | Peds | 170 | |
| BW | 3 | ED | 170 | |
| RW | 3 | ED | 170 | |
| DW | 3 | ED | 150 | |
| RW | 3 | ED | 170 | |

### PGY-2 Residents
| Resident | PGY | Service | Hours/Block Goal | Requests |
|----------|-----|---------|-----------------|----------|
| SAl | 2 | ED | 190 | |
| SAs | 2 | Off-Service | 190 | |
| ABa | 2 | ED | 190 | |
| KB | 2 | ED | 190 | |
| NC | 2 | ED | 190 | |
| JC | 2 | ED | 190 | |
| TC | 2 | Vacation | 190 | |
| ZD | 2 | ED | 190 | |
| IG | 2 | ED | 190 | |
| CH | 2 | ED | 190 | |
| CJ | 2 | ED | 190 | |
| DL | 2 | Off-Service | 190 | |
| NMa | 2 | ED | 190 | |
| VM | 2 | ED | 190 | |
| BMe | 2 | ED | 190 | |
| AMi | 2 | Off-Service | 190 | |
| VR | 2 | ED | 190 | |
| MT | 2 | ED | 190 | |
| ET | 2 | ED | 190 | |
| NY | 2 | ED | 190 | |

### PGY-1 Residents
| Resident | PGY | Service | Hours/Block Goal | Requests |
|----------|-----|---------|-----------------|----------|
| BB | 1 | Peds | 200 | |
| EBe | 1 | Off-Service | 216 | |
| NB | 1 | Off-Service | 216 | |
| EBr | 1 | ED | 216 | |
| MD | 1 | ED | 216 | |
| KF | 1 | Off-Service | 216 | |
| GG | 1 | ED | 216 | 7/8 |
| BH | 1 | ED | 216 | |
| AI | 1 | Peds | 200 | |
| AK | 1 | ED | 216 | |
| RK | 1 | Vacation | 216 | |
| KL | 1 | Off-Service | 216 | |
| AM | 1 | ED | 216 | |
| KM | 1 | Off-Service | 216 | |
| TR | 1 | ED | 216 | |
| KR | 1 | ED | 216 | |
| BS | 1 | ED | 216 | |
| MY | 1 | Peds | 200 | |
| YZ | 1 | ED | 216 | |
| NZ | 1 | Off-Service | 216 | |

## The Schedule/Task
The Google sheets that I'm using to actually schedule the residents appears as below (ignore the grayed out boxes):

[Image of schedule spreadsheet with dates and resident assignments]

The script should print the optimal schedule it comes up with in this format (CSV format) so that I can copy and paste it directly into this sheet. It should also adhere strictly to the shift notation outlined in Shift Details. It should also be able to read Table 2 and understand which residents are available to be scheduled. I should be able to edit this table and it can adapt.

It should also be able to randomize the schedule. In other words, if I run it once and don't like the schedule, I should be able to run it again and have it spit out a slightly different schedule. This is especially helpful when multiple residents have requests and the script can't fulfill all of them at once.