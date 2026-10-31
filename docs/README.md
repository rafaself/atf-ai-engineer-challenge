# Project documentation

Setup and quality commands are in the root README. US-02 adds validated chat and
catalog contracts, structural ports, and the ChatService interface. See
[architecture decisions](adr/README.md) for conventions and ADR-0001.

US-03 implements [catalog import and SQLite retrieval](catalog.md). Provider
execution is available behind the isolated adapter and US-06 implements ChatService
orchestration. The HTTP endpoint remains US-07. Subsequent
documentation will record validated provider decisions and real interactions.
