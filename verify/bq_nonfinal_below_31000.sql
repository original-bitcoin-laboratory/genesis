-- OBL-F-0045: was any NON-FINAL transaction mined below height 31000? (BigQuery public dataset)
-- v0.1 IsFinal (main.h): final if nLockTime == 0; else final if nLockTime < (nLockTime < 500000000
-- ? block height : block time); else final only if EVERY input's nSequence == 0xFFFFFFFF.
-- The block rule (non-final tx => invalid block) arrived in r18 and activated at height 31000.
-- Bounded by block_timestamp_month (partition) so it stays small: height 31000 was mined Dec 2009.
-- Read (1) with (2). If (2) is 0, no transaction below 31000 set a lock time at all, so none could be
-- non-final: the answer is 'none', settled by (2). If (2) > 0 and (1) is empty, every lock-timed tx was
-- final when mined. Only a row in (1) shows a non-final transaction accepted into a block.

-- (1) the answer
SELECT t.block_number, t.hash AS txid, t.lock_time, t.block_timestamp
FROM `bigquery-public-data.crypto_bitcoin.transactions` AS t
WHERE t.block_timestamp_month <= '2009-12-01'
  AND t.block_number < 31000
  AND t.is_coinbase = FALSE
  AND t.lock_time != 0
  AND ( (t.lock_time < 500000000 AND t.lock_time >= t.block_number)
     OR (t.lock_time >= 500000000 AND t.lock_time >= UNIX_SECONDS(t.block_timestamp)) )
  AND EXISTS (SELECT 1 FROM UNNEST(t.inputs) AS i WHERE i.sequence != 4294967295)
ORDER BY t.block_number;

-- (2) the control: how many transactions in the window carry ANY non-zero lock_time
SELECT COUNT(*) AS lock_time_nonzero, COUNTIF(t.is_coinbase) AS of_which_coinbase
FROM `bigquery-public-data.crypto_bitcoin.transactions` AS t
WHERE t.block_timestamp_month <= '2009-12-01'
  AND t.block_number < 31000
  AND t.lock_time != 0;

-- (3) controls for a zero in (2) — a filter that matches nothing also returns zero.
--     (3a) the window is not empty: expect tens of thousands of transactions below height 31000.
--     (3b) the column is populated: nonzero lock_time must appear in a later month (Jan 2016),
--          or the zero in (2) could be a column that is always 0.
SELECT COUNT(*) AS txs_in_window, MIN(block_number) AS first_block, MAX(block_number) AS last_block
FROM `bigquery-public-data.crypto_bitcoin.transactions`
WHERE block_timestamp_month <= '2009-12-01' AND block_number < 31000;

SELECT COUNT(*) AS lock_time_nonzero_jan_2016
FROM `bigquery-public-data.crypto_bitcoin.transactions`
WHERE block_timestamp_month = '2016-01-01' AND lock_time != 0;
