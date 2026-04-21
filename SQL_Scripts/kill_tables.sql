-- =============================================================================
-- DROP ALL TABLES — DataCycle_Warehouse
-- Project: project-d31bc18d-8d9f-48db-a77
-- WARNING: This is irreversible. All data will be permanently deleted.
-- Drop fact tables first to respect FK references, then dimensions.
-- =============================================================================

-- Fact tables
DROP TABLE IF EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.Power_FactTable`;
DROP TABLE IF EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.Weather_FactTable`;
DROP TABLE IF EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.Rooms_FactTable`;
DROP TABLE IF EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.Prediction_FactTable`;

-- Dimension tables
DROP TABLE IF EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimTime`;
DROP TABLE IF EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimInverter`;
DROP TABLE IF EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimConsumption`;
DROP TABLE IF EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimErrors`;
DROP TABLE IF EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimHumidity`;
DROP TABLE IF EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimTemp`;
DROP TABLE IF EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimForecast`;
DROP TABLE IF EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimRoom`;
DROP TABLE IF EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimReservation`;
DROP TABLE IF EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimConsumptionPrediction`;
DROP TABLE IF EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimProductionPrediction`;
DROP TABLE IF EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimProductionPredictionPac`;
DROP TABLE IF EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimProductionPredictionDaysum`;