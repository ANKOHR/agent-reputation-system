# Lessons for KOML

Reliability requires a task definition and recorded acceptance outcome. Mixing task categories or synthetic and real records makes a single aggregate easy to misinterpret, so provenance and group detail must travel with each report.

The deterministic accounting assumption is tested with independent planted counts and a mutation test: changing one success to failure must decrease successes and add its ID to the failure list. This validates computation on controlled data. It does not validate the assumption that operators will record unbiased outcomes or use the tool daily.

Operating rule for future builds: keep expected ground truth independent of the aggregation engine, publish exact traceable counts, and postpone business verdicts until the measured evidence window is complete.
