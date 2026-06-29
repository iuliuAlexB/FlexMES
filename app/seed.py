"""Incarca DB  cu date demo realistice de productie
15 WO-uri finalizate + 1 WO în progres la S4.
1 log pe stație pentru fiecare WO
ISO req: qty_good(Sn) + qty_scrap(Sn) ≤ qty_good(Sn‑1).
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Operation
# (station_id, sequence, op_start_h, op_end_h, log_at_h, source, operator_id)
P001_SCHEDULE = [
    (1, 1, 0.0, 1.0,  0.5,  "mqtt",   1),  # S1 Debitare
    (2, 2, 1.0, 2.0,  1.5,  "mqtt",   1),  # S2 Modelare
    (3, 3, 2.0, 3.5,  2.75, "mqtt",   1),  # S3 Finisare
    (4, 4, 3.5, 5.0,  4.25, "manual", 3),  # S4 Inspecție QC
]
P002_SCHEDULE = [
    (1, 1, 0.0, 1.0,  0.5,  "mqtt",   1),  # S1 Debitare
    (2, 2, 1.0, 2.0,  1.5,  "mqtt",   1),  # S2 Modelare
    (4, 3, 2.0, 3.5,  2.75, "manual", 3),  # S4 Inspecție QC
]
SCHEDULES = {1: P001_SCHEDULE, 2: P002_SCHEDULE}
DURATIONS = {1: 5.0, 2: 3.5}

# WO
# (wo_id, order_number, product_id, qty_planned, days_ago,
#  {station_id: (qty_good, qty_scrap, is_anomaly)})
# Regula ISO pt WO:qty_good(Sn) + qty_scrap(Sn) ≤ qty_good(Sn-1)
WO_DEFS = [
    (1,  "WO-001", 1, 100, 15, {
        1: (94, 6,  False),   # S1: 94+6=100 ≤ 100 ✓
        2: (89, 4,  False),   # S2: 89+4=93  ≤ 94  ✓
        3: (85, 3,  False),   # S3: 85+3=88  ≤ 89  ✓
        4: (81, 4,  False),   # S4: 81+4=85  ≤ 85  ✓  FPY=81%
    }),
    (2,  "WO-002", 2,  80, 14, {
        1: (76, 4,  False),   # S1: 76+4=80  ≤ 80  ✓
        2: (72, 3,  False),   # S2: 72+3=75  ≤ 76  ✓
        4: (69, 3,  False),   # S4: 69+3=72  ≤ 72  ✓  FPY=86.25%
    }),
    (3,  "WO-003", 1, 100, 13, {
        1: (93, 7,  False),
        2: (88, 4,  False),   # 92 ≤ 93 ✓
        3: (84, 3,  False),   # 87 ≤ 88 ✓
        4: (80, 4,  False),   # 84 ≤ 84 ✓  FPY=80%
    }),
    (4,  "WO-004", 2,  80, 12, {
        1: (75, 5,  False),
        2: (71, 3,  False),   # 74 ≤ 75 ✓
        4: (68, 3,  False),   # 71 ≤ 71 ✓  FPY=85%
    }),
    (5,  "WO-005", 1, 100, 11, {
        1: (94, 6,  False),
        2: (89, 4,  False),   # 93 ≤ 94 ✓
        3: (15, 70, True),    # ANOMALIE S3 — scrap rate 82%
        4: (13, 2,  False),   # 15 ≤ 15 ✓  FPY=13%
    }),
    (6,  "WO-006", 2,  80, 10, {
        1: (77, 3,  False),
        2: (73, 3,  False),   # 76 ≤ 77 ✓
        4: (70, 3,  False),   # 73 ≤ 73 ✓  FPY=87.5%
    }),
    (7,  "WO-007", 1, 100,  9, {
        1: (92, 8,  False),
        2: (87, 4,  False),   # 91 ≤ 92 ✓
        3: (83, 3,  False),   # 86 ≤ 87 ✓
        4: (79, 4,  False),   # 83 ≤ 83 ✓  FPY=79%
    }),
    (8,  "WO-008", 2,  80,  8, {
        1: (76, 4,  False),
        2: (12, 58, True),    # ANOMALIE S2 — scrap rate 83%
        4: (10, 2,  False),   # 12 ≤ 12 ✓  FPY=12.5%
    }),
    (9,  "WO-009", 1, 100,  7, {
        1: (95, 5,  False),
        2: (90, 4,  False),   # 94 ≤ 95 ✓
        3: (86, 3,  False),   # 89 ≤ 90 ✓
        4: (82, 4,  False),   # 86 ≤ 86 ✓  FPY=82%
    }),
    (10, "WO-010", 2,  80,  6, {
        1: (74, 6,  False),
        2: (70, 3,  False),   # 73 ≤ 74 ✓
        4: (67, 3,  False),   # 70 ≤ 70 ✓  FPY=83.75%
    }),
    (11, "WO-011", 1, 100,  5, {
        1: (93, 7,  False),
        2: (88, 4,  False),   # 92 ≤ 93 ✓
        3: (84, 3,  False),   # 87 ≤ 88 ✓
        4: (80, 4,  False),   # 84 ≤ 84 ✓  FPY=80%
    }),
    (12, "WO-012", 2,  80,  4, {
        1: (76, 4,  False),
        2: (72, 3,  False),   # 75 ≤ 76 ✓
        4: (69, 3,  False),   # 72 ≤ 72 ✓  FPY=86.25%
    }),
    (13, "WO-013", 1, 100,  3, {
        1: (94, 6,  False),
        2: (89, 4,  False),   # 93 ≤ 94 ✓
        3: (85, 3,  False),   # 88 ≤ 89 ✓
        4: (8,  72, True),    # ANOMALIE S4 — scrap rate 90%  FPY=8%
    }),
    (14, "WO-014", 2,  80,  2, {
        1: (75, 5,  False),
        2: (71, 3,  False),   # 74 ≤ 75 ✓
        4: (68, 3,  False),   # 71 ≤ 71 ✓  FPY=85%
    }),
    (15, "WO-015", 1, 100,  1, {
        1: (92, 8,  False),
        2: (87, 4,  False),   # 91 ≤ 92 ✓
        3: (83, 3,  False),   # 86 ≤ 87 ✓
        4: (79, 4,  False),   # 83 ≤ 83 ✓  FPY=79%
    }),
]


def run_seed(db: Session) -> None:
    from models import Station

    if db.query(Station).count() > 0:
        return  # Already seeded

    now = datetime.utcnow()

    #Users
    db.execute(text("""
        INSERT INTO users (id, username, password_hash, role, is_active, created_at) VALUES
        (1, 'mqtt_system', :ph1, 'system',   true, :now),
        (2, 'admin',       :ph2, 'manager',  true, :now),
        (3, 'operator1',   :ph3, 'operator', true, :now)
        ON CONFLICT (id) DO NOTHING
    """), {
        "ph1": pwd_context.hash("system"),
        "ph2": pwd_context.hash("admin123"),
        "ph3": pwd_context.hash("op123"),
        "now": now,
    })

    #Products
    db.execute(text("""
        INSERT INTO products (id, code, name, is_active, created_at) VALUES
        (1, 'P001', 'Carcasă Metalică', true, :now),
        (2, 'P002', 'Capac Plastic',    true, :now)
        ON CONFLICT (id) DO NOTHING
    """), {"now": now})

    # Stations
    db.execute(text("""
        INSERT INTO stations (id, code, name, sequence) VALUES
        (1, 'S1', 'Debitare',     1),
        (2, 'S2', 'Modelare',     2),
        (3, 'S3', 'Finisare',     3),
        (4, 'S4', 'Inspecție QC', 4)
        ON CONFLICT (id) DO NOTHING
    """))

    # Routings
    db.execute(text("""
        INSERT INTO routings (product_id, station_id, sequence) VALUES
        (1,1,1),(1,2,2),(1,3,3),(1,4,4),
        (2,1,1),(2,2,2),(2,4,3)
        ON CONFLICT DO NOTHING
    """))

    # WO completed
    op_id  = 1
    log_id = 1

    for wo_id, order_num, prod_id, qty, days_ago, logs in WO_DEFS:
        t0 = now - timedelta(days=days_ago)
        t1 = t0 + timedelta(hours=DURATIONS[prod_id])
        schedule = SCHEDULES[prod_id]

        #WO
        db.execute(text("""
            INSERT INTO work_orders
                (id, order_number, product_id, qty_planned, status,
                 created_at, started_at, completed_at, created_by)
            VALUES (:id,:num,:pid,:qty,'completed',:t0,:t0,:t1,2)
            ON CONFLICT (id) DO NOTHING
        """), {"id": wo_id, "num": order_num, "pid": prod_id,
               "qty": qty, "t0": t0, "t1": t1})

        # Operations + Logs
        op_ids = {}  # station_id → op_id
        for st_id, seq, op_start_h, op_end_h, log_h, source, oper_id in schedule:
            op_t0 = t0 + timedelta(hours=op_start_h)
            op_t1 = t0 + timedelta(hours=op_end_h)

            db.execute(text("""
                INSERT INTO operations
                    (id, work_order_id, station_id, sequence, status,
                     started_at, completed_at, started_by)
                VALUES (:id,:wo,:st,:seq,'completed',:t0,:t1,1)
                ON CONFLICT (id) DO NOTHING
            """), {"id": op_id, "wo": wo_id, "st": st_id,
                   "seq": seq, "t0": op_t0, "t1": op_t1})
            op_ids[st_id] = op_id
            op_id += 1

            good, scrap, anom = logs[st_id]
            db.execute(text("""
                INSERT INTO production_logs
                    (id, operation_id, work_order_id, station_id, operator_id,
                     qty_good, qty_scrap, logged_at, source, is_anomaly)
                VALUES (:id,:op,:wo,:st,:oper,:good,:scrap,:ts,:src,:anom)
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": log_id, "op": op_ids[st_id], "wo": wo_id,
                "st": st_id, "oper": oper_id, "good": good,
                "scrap": scrap, "ts": t0 + timedelta(hours=log_h),
                "src": source, "anom": anom
            })
            log_id += 1

    # ─────────────────────────────────────────────────────────────────────────
    # WO-016: P002 — IN PROGRESS la S4 (demo live)
    # Pornit acum 2 ore, S1 și S2 completate, S4 in_progress
    # S1: 74 good, 6 scrap → input=80
    # S2: 70 good, 3 scrap → 73 ≤ 74 ✓
    # ─────────────────────────────────────────────────────────────────────────
    t16 = now - timedelta(hours=2)

    db.execute(text("""
        INSERT INTO work_orders
            (id, order_number, product_id, qty_planned, status,
             created_at, started_at, created_by)
        VALUES (16,'WO-016',2,80,'in_progress',:t0,:t0,2)
        ON CONFLICT (id) DO NOTHING
    """), {"t0": t16})

    db.execute(text("""
        INSERT INTO operations
            (id, work_order_id, station_id, sequence, status,
             started_at, completed_at, started_by) VALUES
        (:op1, 16, 1, 1, 'completed',   :t0, :t1, 1),
        (:op2, 16, 2, 2, 'completed',   :t1, :t2, 1),
        (:op3, 16, 4, 3, 'in_progress', :t2, NULL, 1)
        ON CONFLICT (id) DO NOTHING
    """), {
        "op1": op_id, "op2": op_id + 1, "op3": op_id + 2,
        "t0": t16,
        "t1": t16 + timedelta(minutes=45),
        "t2": t16 + timedelta(hours=1, minutes=30),
    })

    db.execute(text("""
        INSERT INTO production_logs
            (id, operation_id, work_order_id, station_id, operator_id,
             qty_good, qty_scrap, logged_at, source, is_anomaly)
        VALUES
        (:id1, :op1, 16, 1, 1, 74, 6, :t1, 'mqtt',   false),
        (:id2, :op2, 16, 2, 1, 70, 3, :t2, 'mqtt',   false)
        ON CONFLICT (id) DO NOTHING
    """), {
        "id1": log_id, "id2": log_id + 1,
        "op1": op_id, "op2": op_id + 1,
        "t1": t16 + timedelta(minutes=30),
        "t2": t16 + timedelta(hours=1, minutes=15),
    })

    # Sequences
    db.execute(text("SELECT setval('users_id_seq',           (SELECT MAX(id) FROM users))"))
    db.execute(text("SELECT setval('products_id_seq',        (SELECT MAX(id) FROM products))"))
    db.execute(text("SELECT setval('stations_id_seq',        (SELECT MAX(id) FROM stations))"))
    db.execute(text("SELECT setval('work_orders_id_seq',     (SELECT MAX(id) FROM work_orders))"))
    db.execute(text("SELECT setval('operations_id_seq',      (SELECT MAX(id) FROM operations))"))
    db.execute(text("SELECT setval('production_logs_id_seq', (SELECT MAX(id) FROM production_logs))"))
    db.execute(text("SELECT setval('routings_id_seq',        (SELECT MAX(id) FROM routings))"))

    db.commit()