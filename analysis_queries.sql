-- P-card audit assignment: Parts II and III
-- Population used throughout: Oklahoma State University, calendar year 2014.

DROP VIEW IF EXISTS qry_T2_Question1;
CREATE VIEW qry_T2_Question1 AS
SELECT FullName,
       ROUND(SUM(Amount), 2) AS TotalAmount
FROM pcards
WHERE Year = 2014
  AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
GROUP BY FullName
HAVING SUM(Amount) > 50000
ORDER BY TotalAmount DESC;

DROP VIEW IF EXISTS qry_T2_Question2;
CREATE VIEW qry_T2_Question2 AS
SELECT FullName,
       Month,
       ROUND(SUM(Amount), 2) AS TotalAmount
FROM pcards
WHERE Year = 2014
  AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
GROUP BY FullName, Month
HAVING SUM(Amount) > 10000
ORDER BY Month ASC, TotalAmount DESC;

DROP VIEW IF EXISTS qry_T2_Question3;
CREATE VIEW qry_T2_Question3 AS
SELECT Amount, FullName, Description, Vendor,
       TransactionDate, PostedDate, MCC
FROM pcards
WHERE Year = 2014
  AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
  AND Amount > 5000
ORDER BY Amount DESC;

DROP VIEW IF EXISTS qry_T2_Question4;
CREATE VIEW qry_T2_Question4 AS
WITH flagged AS (
    SELECT FullName, Vendor, TransactionDate
    FROM pcards
    WHERE Year = 2014
      AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
      AND Amount > 0
    GROUP BY FullName, Vendor, TransactionDate
    HAVING COUNT(*) > 1 AND SUM(Amount) > 5000
)
SELECT p.Amount, p.FullName, p.Description, p.Vendor,
       p.TransactionDate, p.PostedDate, p.MCC
FROM pcards AS p
JOIN flagged AS f
  ON p.FullName = f.FullName
 AND p.Vendor = f.Vendor
 AND p.TransactionDate = f.TransactionDate
WHERE p.Year = 2014
  AND p.AgencyName = 'OKLAHOMA STATE UNIVERSITY'
  AND p.Amount > 0
ORDER BY p.Month ASC,
         CAST(substr(p.TransactionDate,
              instr(p.TransactionDate, '/') + 1,
              instr(substr(p.TransactionDate,
                  instr(p.TransactionDate, '/') + 1), '/') - 1) AS INTEGER) ASC,
         p.FullName, p.Vendor, p.Amount DESC;

DROP VIEW IF EXISTS qry_T2_Question5;
CREATE VIEW qry_T2_Question5 AS
WITH flagged AS (
    SELECT Vendor, TransactionDate
    FROM pcards
    WHERE Year = 2014
      AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
      AND Amount > 0
    GROUP BY Vendor, TransactionDate
    HAVING COUNT(*) = 2
       AND COUNT(DISTINCT FullName) = 2
       AND SUM(Amount) > 5000
)
SELECT p.Amount, p.FullName, p.Description, p.Vendor,
       p.TransactionDate, p.PostedDate, p.MCC
FROM pcards AS p
JOIN flagged AS f
  ON p.Vendor = f.Vendor
 AND p.TransactionDate = f.TransactionDate
WHERE p.Year = 2014
  AND p.AgencyName = 'OKLAHOMA STATE UNIVERSITY'
  AND p.Amount > 0
ORDER BY p.Month ASC,
         CAST(substr(p.TransactionDate,
              instr(p.TransactionDate, '/') + 1,
              instr(substr(p.TransactionDate,
                  instr(p.TransactionDate, '/') + 1), '/') - 1) AS INTEGER) ASC,
         p.Vendor, p.FullName;

DROP VIEW IF EXISTS qry_T2_Question6;
CREATE VIEW qry_T2_Question6 AS
WITH flagged AS (
    SELECT FullName, TransactionDate
    FROM pcards
    WHERE Year = 2014
      AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
      AND Amount > 0
    GROUP BY FullName, TransactionDate
    HAVING COUNT(*) = 2
       AND COUNT(DISTINCT Vendor) = 2
       AND SUM(Amount) > 5000
)
SELECT p.Amount, p.FullName, p.Description, p.Vendor,
       p.TransactionDate, p.PostedDate, p.MCC
FROM pcards AS p
JOIN flagged AS f
  ON p.FullName = f.FullName
 AND p.TransactionDate = f.TransactionDate
WHERE p.Year = 2014
  AND p.AgencyName = 'OKLAHOMA STATE UNIVERSITY'
  AND p.Amount > 0
ORDER BY p.Month ASC,
         CAST(substr(p.TransactionDate,
              instr(p.TransactionDate, '/') + 1,
              instr(substr(p.TransactionDate,
                  instr(p.TransactionDate, '/') + 1), '/') - 1) AS INTEGER) ASC,
         p.FullName, p.Vendor;

DROP VIEW IF EXISTS qry_T2_Question7;
CREATE VIEW qry_T2_Question7 AS
WITH matched_days AS (
    SELECT FullName, TransactionDate
    FROM pcards
    WHERE Year = 2014
      AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
    GROUP BY FullName, TransactionDate
    HAVING SUM(CASE WHEN lower(MCC) LIKE '%hotel%'
                          OR lower(MCC) LIKE '%motel%'
                          OR lower(MCC) LIKE '%resort%'
                          OR lower(MCC) LIKE '%inn%'
                    THEN 1 ELSE 0 END) > 0
       AND SUM(CASE WHEN lower(MCC) LIKE '%food%'
                          OR lower(MCC) LIKE '%restaurant%'
                    THEN 1 ELSE 0 END) > 0
)
SELECT p.Amount, p.FullName, p.Description, p.Vendor,
       p.TransactionDate, p.PostedDate, p.MCC
FROM pcards AS p
JOIN matched_days AS d
  ON p.FullName = d.FullName
 AND p.TransactionDate = d.TransactionDate
WHERE p.Year = 2014
  AND p.AgencyName = 'OKLAHOMA STATE UNIVERSITY'
  AND (lower(p.MCC) LIKE '%hotel%'
       OR lower(p.MCC) LIKE '%motel%'
       OR lower(p.MCC) LIKE '%resort%'
       OR lower(p.MCC) LIKE '%inn%'
       OR lower(p.MCC) LIKE '%food%'
       OR lower(p.MCC) LIKE '%restaurant%')
ORDER BY p.FullName ASC, p.Amount ASC;

-- Student-defined internal-control tests

DROP VIEW IF EXISTS qry_T2_Question8;
CREATE VIEW qry_T2_Question8 AS
SELECT Amount, FullName, Description, Vendor,
       TransactionDate, PostedDate, MCC
FROM pcards
WHERE Year = 2014
  AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
  AND Amount > 0
  AND lower(Description) LIKE '%tax%'
ORDER BY Amount DESC;

DROP VIEW IF EXISTS qry_T2_Question9;
CREATE VIEW qry_T2_Question9 AS
SELECT Amount, FullName, Description, Vendor,
       TransactionDate, PostedDate, MCC
FROM pcards
WHERE Year = 2014
  AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
  AND Amount > 0
  AND (lower(MCC) LIKE '%liquor%'
       OR lower(MCC) LIKE '%beer%'
       OR lower(MCC) LIKE '%wine%'
       OR lower(MCC) LIKE '%alcohol%'
       OR lower(Description) LIKE '%alcohol%')
ORDER BY Amount DESC;

DROP VIEW IF EXISTS qry_T2_Question10;
CREATE VIEW qry_T2_Question10 AS
SELECT Amount, FullName, Description, Vendor,
       TransactionDate, PostedDate, MCC
FROM pcards
WHERE Year = 2014
  AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
  AND Amount > 0
  AND (lower(MCC) LIKE '%gasoline%'
       OR lower(MCC) LIKE '%fuel%'
       OR lower(MCC) LIKE '%service station%')
ORDER BY Amount DESC;

DROP VIEW IF EXISTS qry_T2_Question11;
CREATE VIEW qry_T2_Question11 AS
SELECT Amount, FullName, Description, Vendor,
       TransactionDate, PostedDate, MCC
FROM pcards
WHERE Year = 2014
  AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
  AND Amount > 0
  AND (lower(MCC) LIKE '%postal%'
       OR lower(MCC) LIKE '%courier%'
       OR lower(MCC) LIKE '%mail%'
       OR lower(Vendor) LIKE '%post office%'
       OR lower(Vendor) LIKE '%usps%')
ORDER BY Amount DESC;

DROP VIEW IF EXISTS qry_T2_Question12;
CREATE VIEW qry_T2_Question12 AS
SELECT Amount, FullName, Description, Vendor,
       TransactionDate, PostedDate, MCC
FROM pcards
WHERE Year = 2014
  AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
  AND Amount > 0
  AND (lower(MCC) LIKE '%insurance%'
       OR lower(Description) LIKE '%insurance%')
ORDER BY Amount DESC;

DROP VIEW IF EXISTS qry_T2_Question13;
CREATE VIEW qry_T2_Question13 AS
SELECT Amount, FullName, Description, Vendor,
       TransactionDate, PostedDate, MCC
FROM pcards
WHERE Year = 2014
  AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
  AND Amount > 0
  AND (lower(MCC) LIKE '%membership%'
       OR lower(MCC) LIKE '%organization%'
       OR lower(Description) LIKE '%membership%'
       OR lower(Description) LIKE '%dues%')
ORDER BY Amount DESC;

DROP VIEW IF EXISTS qry_T2_Question14;
CREATE VIEW qry_T2_Question14 AS
SELECT Amount, FullName, Description, Vendor,
       TransactionDate, PostedDate, MCC
FROM pcards
WHERE Year = 2014
  AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
  AND Amount > 0
  AND (lower(MCC) LIKE '%gift%'
       OR lower(Description) LIKE '%gift card%'
       OR lower(Description) LIKE '%gift certificate%'
       OR lower(Vendor) LIKE '%gift card%')
ORDER BY Amount DESC;

-- Part III: forensic data analysis

DROP VIEW IF EXISTS qry_T3_Question1;
CREATE VIEW qry_T3_Question1 AS
WITH RECURSIVE digits(Digit) AS (
    SELECT 1
    UNION ALL
    SELECT Digit + 1 FROM digits WHERE Digit < 9
),
first_digits AS (
    SELECT CAST(substr(printf('%.2f', Amount), 1, 1) AS INTEGER) AS Digit
    FROM pcards
    WHERE Year = 2014
      AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
      AND Amount >= 1.00
)
SELECT d.Digit,
       ROUND(100.0 * COUNT(f.Digit) / (SELECT COUNT(*) FROM first_digits), 3)
           AS ActualPercentage
FROM digits AS d
LEFT JOIN first_digits AS f ON f.Digit = d.Digit
GROUP BY d.Digit
ORDER BY d.Digit;

DROP VIEW IF EXISTS qry_T3_Question2;
CREATE VIEW qry_T3_Question2 AS
WITH duplicate_groups AS (
    SELECT TransactionDate, Vendor, CardholderFirstInitial,
           CardholderLastName, Amount
    FROM pcards
    WHERE Year = 2014
      AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
      AND Amount > 0
    GROUP BY TransactionDate, Vendor, CardholderFirstInitial,
             CardholderLastName, Amount
    HAVING COUNT(*) >= 2
)
SELECT p.TransactionDate, p.Vendor, p.FullName, p.Amount
FROM pcards AS p
JOIN duplicate_groups AS d
  ON p.TransactionDate = d.TransactionDate
 AND p.Vendor = d.Vendor
 AND p.CardholderFirstInitial = d.CardholderFirstInitial
 AND p.CardholderLastName = d.CardholderLastName
 AND p.Amount = d.Amount
WHERE p.Year = 2014
  AND p.AgencyName = 'OKLAHOMA STATE UNIVERSITY'
  AND p.Amount > 0
ORDER BY p.Month ASC,
         CAST(substr(p.TransactionDate,
              instr(p.TransactionDate, '/') + 1,
              instr(substr(p.TransactionDate,
                  instr(p.TransactionDate, '/') + 1), '/') - 1) AS INTEGER) ASC,
         p.Vendor ASC;

DROP VIEW IF EXISTS qry_T3_Question3;
CREATE VIEW qry_T3_Question3 AS
WITH duplicate_occasions AS (
    SELECT FullName, TransactionDate, Vendor, Amount
    FROM pcards
    WHERE Year = 2014
      AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
      AND Amount > 0
    GROUP BY FullName, TransactionDate, Vendor,
             CardholderFirstInitial, CardholderLastName, Amount
    HAVING COUNT(*) >= 2
)
SELECT FullName, COUNT(*) AS DuplicateOccasions
FROM duplicate_occasions
GROUP BY FullName
HAVING COUNT(*) > 1
ORDER BY DuplicateOccasions DESC, FullName ASC;

DROP VIEW IF EXISTS qry_T3_Question4;
CREATE VIEW qry_T3_Question4 AS
SELECT Amount, Vendor, Description, FullName
FROM pcards
WHERE Year = 2014
  AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
  AND Amount > 0
  AND CAST(Amount AS INTEGER) BETWEEN 1000 AND 9999
  AND CAST(Amount AS INTEGER) % 1000 = 0
ORDER BY Vendor ASC, FullName ASC;

-- Student-defined fraud tests

DROP VIEW IF EXISTS qry_T3_Question5;
CREATE VIEW qry_T3_Question5 AS
WITH dated AS (
    SELECT *,
           printf('%04d-%02d-%02d',
                  Year,
                  Month,
                  CAST(substr(
                      TransactionDate,
                      instr(TransactionDate, '/') + 1,
                      instr(substr(TransactionDate,
                          instr(TransactionDate, '/') + 1), '/') - 1
                  ) AS INTEGER)) AS ISOTransactionDate
    FROM pcards
    WHERE Year = 2014
      AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
      AND Amount >= 500
)
SELECT Amount, FullName, Description, Vendor,
       TransactionDate, PostedDate, MCC
FROM dated
WHERE strftime('%w', ISOTransactionDate) IN ('0', '6')
ORDER BY Amount DESC;

DROP VIEW IF EXISTS qry_T3_Question6;
CREATE VIEW qry_T3_Question6 AS
SELECT Amount, FullName, Description, Vendor,
       TransactionDate, PostedDate, MCC
FROM pcards
WHERE Year = 2014
  AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
  AND Amount BETWEEN 4750 AND 5000
ORDER BY Amount DESC, FullName ASC;

DROP VIEW IF EXISTS qry_T3_Question7;
CREATE VIEW qry_T3_Question7 AS
WITH dated AS (
    SELECT *,
           printf('%04d-%02d-%02d',
                  Year,
                  Month,
                  CAST(substr(
                      TransactionDate,
                      instr(TransactionDate, '/') + 1,
                      instr(substr(TransactionDate,
                          instr(TransactionDate, '/') + 1), '/') - 1
                  ) AS INTEGER)) AS ISOTransactionDate
    FROM pcards
    WHERE Year = 2014
      AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
      AND Amount >= 100
)
SELECT FullName, Vendor, Amount,
       COUNT(*) AS TransactionCount,
       COUNT(DISTINCT TransactionDate) AS DistinctDates,
       ROUND(SUM(Amount), 2) AS TotalAmount,
       MIN(ISOTransactionDate) AS FirstTransactionDate,
       MAX(ISOTransactionDate) AS LastTransactionDate
FROM dated
GROUP BY FullName, Vendor, Amount
HAVING COUNT(DISTINCT TransactionDate) >= 5
ORDER BY TransactionCount DESC, TotalAmount DESC;

DROP VIEW IF EXISTS qry_T3_Question8;
CREATE VIEW qry_T3_Question8 AS
WITH vendor_totals AS (
    SELECT Vendor, SUM(Amount) AS VendorTotal
    FROM pcards
    WHERE Year = 2014
      AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
      AND Amount > 0
    GROUP BY Vendor
    HAVING SUM(Amount) >= 10000
),
employee_vendor AS (
    SELECT FullName, Vendor,
           COUNT(*) AS TransactionCount,
           SUM(Amount) AS EmployeeVendorTotal
    FROM pcards
    WHERE Year = 2014
      AND AgencyName = 'OKLAHOMA STATE UNIVERSITY'
      AND Amount > 0
    GROUP BY FullName, Vendor
    HAVING COUNT(*) >= 5
)
SELECT e.FullName, e.Vendor, e.TransactionCount,
       ROUND(e.EmployeeVendorTotal, 2) AS EmployeeVendorTotal,
       ROUND(v.VendorTotal, 2) AS VendorTotal,
       ROUND(100.0 * e.EmployeeVendorTotal / v.VendorTotal, 2)
           AS EmployeeSharePercentage
FROM employee_vendor AS e
JOIN vendor_totals AS v ON v.Vendor = e.Vendor
WHERE e.EmployeeVendorTotal / v.VendorTotal >= 0.80
ORDER BY EmployeeSharePercentage DESC, EmployeeVendorTotal DESC;
