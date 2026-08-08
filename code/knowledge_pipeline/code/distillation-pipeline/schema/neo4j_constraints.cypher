/*
 * Neo4j Schema-Constraints für die migrierte Ontologie.
 *
 * Führe diesen Block EINMALIG aus, bevor das erste Paper ingestet wird.
 * Constraints stellen sicher, dass MERGE über Papers hinweg korrekt
 * funktioniert (doppelte Technologien werden nicht erstellt).
 *
 * Neo4j 5.x Syntax —Enterprise Edition empfohlen.
 */

// ===================================================================
// UNIQUE-CONSTRAINTS für persistente Node-IDs (Ebene 1 + 3)
// ===================================================================

// Technology: Jeder kanonisierte Name ergibt denselben Knoten.
CREATE CONSTRAINT technology_id IF NOT EXISTS
  FOR (n:Technology) REQUIRE n.id IS UNIQUE;

// Problem: Jeder kanonisierte Name ergibt denselben Knoten.
CREATE CONSTRAINT problem_id IF NOT EXISTS
  FOR (n:Problem) REQUIRE n.id IS UNIQUE;

// Capability: Jeder kanonisierte Name ergibt denselben Knoten.
CREATE CONSTRAINT capability_id IF NOT EXISTS
  FOR (n:Capability) REQUIRE n.id IS UNIQUE;

// Metric: Jeder kanonisierte Name ergibt denselben Knoten.
CREATE CONSTRAINT metric_id IF NOT EXISTS
  FOR (n:Metric) REQUIRE n.id IS UNIQUE;

// Dataset: Jeder kanonisierte Name ergibt denselben Knoten.
CREATE CONSTRAINT dataset_id IF NOT EXISTS
  FOR (n:Dataset) REQUIRE n.id IS UNIQUE;

// Assumption: Reifiziert auf Ebene 1 — kanonisierte Statement.
CREATE CONSTRAINT assumption_id IF NOT EXISTS
  FOR (n:Assumption) REQUIRE n.id IS UNIQUE;

// Limitation: Reifiziert auf Ebene 1 — kanonisierte Statement.
CREATE CONSTRAINT limitation_id IF NOT EXISTS
  FOR (n:Limitation) REQUIRE n.id IS UNIQUE;

// Paper: DOI als Stable-ID, wo verfügbar.
CREATE CONSTRAINT paper_id IF NOT EXISTS
  FOR (n:Paper) REQUIRE n.id IS UNIQUE;

// Author: ORCID wo verfügbar, sonst (name + affiliation).
CREATE CONSTRAINT author_id IF NOT EXISTS
  FOR (n:Author) REQUIRE n.id IS UNIQUE;

// Organization: Kanonisierte Name.
CREATE CONSTRAINT organization_id IF NOT EXISTS
  FOR (n:Organization) REQUIRE n.id IS UNIQUE;

// FundingSource: Kanonisierte Name.
CREATE CONSTRAINT fundingsource_id IF NOT EXISTS
  FOR (n:FundingSource) REQUIRE n.id IS UNIQUE;

// Venue: Kanonisierte Name + tier.
CREATE CONSTRAINT venue_id IF NOT EXISTS
  FOR (n:Venue) REQUIRE n.id IS UNIQUE;

// ===================================================================
// INDEXE für häufig abgefragte Felder (Performance)
// ===================================================================

CREATE INDEX technology_name IF NOT EXISTS
  FOR (n:Technology) ON (n.name);

CREATE INDEX paper_year IF NOT EXISTS
  FOR (n:Paper) ON (n.year);

CREATE INDEX paper_doi IF NOT EXISTS
  FOR (n:Paper) ON (n.doi);

CREATE INDEX paper_peer_reviewed IF NOT EXISTS
  FOR (n:Paper) ON (n.peerReviewed);

CREATE INDEX claim_polarity IF NOT EXISTS
  FOR (n:Claim) ON (n.polarity);

CREATE INDEX claim_type IF NOT EXISTS
  FOR (n:Claim) ON (n.claimType);

CREATE INDEX experiment_type IF NOT EXISTS
  FOR (n:Experiment) ON (n.experimentType);

CREATE INDEX experiment_leakage_risk IF NOT EXISTS
  FOR (n:Experiment) ON (n.leakageRisk);

CREATE INDEX evidence_type IF NOT EXISTS
  FOR (n:Evidence) ON (n.type);

CREATE INDEX technology_aliases IF NOT EXISTS
  FOR (n:Technology) ON (n.aliases);

CREATE INDEX dataset_contamination_risk IF NOT EXISTS
  FOR (n:Dataset) ON (n.contaminationRisk);

CREATE INDEX venue_tier IF NOT EXISTS
  FOR (n:Venue) ON (n.tier);

// ===================================================================
// INDEXE für epistemik-Knoten (optional, erst wenn Datenmenge groß)
// ===================================================================

// Erklärung: Claims und Evidence sind paper-scoped (CREATE).
// Indices werden nur relevant, wenn du über den ganzen Graphen
// über Claims nach polarity filterst (>10.000 Claims).

CREATE INDEX claim_extraction_confidence IF NOT EXISTS
  FOR (n:Claim) ON (n.extractionConfidence);

CREATE INDEX evidence_extraction_confidence IF NOT EXISTS
  FOR (n:Evidence) ON (n.extractionConfidence);

// ===================================================================
// STATUS PRÜFEN (nach dem Ausführen)
// ===================================================================

// Alle Constraints anzeigen:
// SHOW CONSTRAINTS;

// Alle Indices anzeigen:
// SHOW INDEXES;
