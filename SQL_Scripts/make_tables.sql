-- =============================================================================
-- GOLD LAYER — BigQuery DDL
-- Galaxy Schema: Energy Monitoring, Weather, Room Reservations & Predictions
-- Project:  project-d31bc18d-8d9f-48db-a77
-- Dataset:  DataCycle_Warehouse
-- Key types: RoomID → INT64 | all other *ID/*Key columns → STRING (UUID)
-- Partitioning: all fact tables partitioned by partition_date DATE
-- Changes:  + Year added to DimTime
--           + FactID surrogate PK added to all fact tables
-- =============================================================================


-- =============================================================================
-- DIMENSION TABLES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- DimTime
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimTime` (
  TimeID    STRING  NOT NULL,  -- UUID
  Year      INT64,             -- Calendar year (e.g. 2024)
  Month     INT64,             -- Month (1–12)
  Day       INT64,             -- Day of month (1–31)
  Hour      INT64,             -- Hour (0–23)
  Minute    INT64,             -- Minute (0–59)
  Second    INT64              -- Second (0–59)
)
OPTIONS (description = 'Time dimension shared by all fact tables');


-- -----------------------------------------------------------------------------
-- DimInverter  (UUID surrogate PK + INT64 natural key)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimInverter` (
  InverterKey STRING  NOT NULL,  -- UUID surrogate PK
  InverterID  INT64,             -- Natural/business key (inverter number)
  PAC         FLOAT64,           -- Active power output (W)
  Daysum      FLOAT64,           -- Total energy produced today (Wh)
  PDC1        FLOAT64,           -- DC power input string 1
  PDC2        FLOAT64,           -- DC power input string 2
  UDC1        FLOAT64,           -- DC voltage string 1
  UDC2        FLOAT64,           -- DC voltage string 2
  Status      STRING             -- Operational status
)
OPTIONS (description = 'Solar inverter dimension with production metrics');


-- -----------------------------------------------------------------------------
-- DimConsumption
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimConsumption` (
  ConsumptionID STRING  NOT NULL,  -- UUID
  Value         FLOAT64,           -- Consumption value (kWh)
  Variation     FLOAT64            -- Delta vs previous reading
)
OPTIONS (description = 'Energy consumption dimension');


-- -----------------------------------------------------------------------------
-- DimErrors
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimErrors` (
  ErrorID     STRING  NOT NULL,  -- UUID
  Error_info  STRING             -- Error description or fault code
)
OPTIONS (description = 'Error and fault codes for inverters');


-- -----------------------------------------------------------------------------
-- DimHumidity
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimHumidity` (
  HumidityID  STRING  NOT NULL,  -- UUID
  Value       FLOAT64,           -- Humidity (%)
  Variation   FLOAT64            -- Delta vs previous reading
)
OPTIONS (description = 'Humidity sensor dimension');


-- -----------------------------------------------------------------------------
-- DimTemp
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimTemp` (
  TempID     STRING  NOT NULL,  -- UUID
  Value      FLOAT64,           -- Temperature (°C)
  Variation  FLOAT64            -- Delta vs previous reading
)
OPTIONS (description = 'Temperature sensor dimension');


-- -----------------------------------------------------------------------------
-- DimForecast
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimForecast` (
  ForecastID   STRING  NOT NULL,  -- UUID
  Site         STRING,            -- Location/site identifier
  Measurement  STRING,            -- Type of measurement (e.g. temperature, irradiance)
  Value        FLOAT64,           -- Observed value
  Prediction   FLOAT64,           -- Model prediction value
  Unit         STRING             -- Unit of measurement
)
OPTIONS (description = 'Weather forecast dimension');


-- -----------------------------------------------------------------------------
-- DimRoom  (INT64 PK — no surrogate key by design)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimRoom` (
  RoomID        INT64   NOT NULL,  -- Integer PK (natural key from source)
  Alt_RoomID    STRING,            -- Alternative / external room identifier
  FullName      STRING,            -- Full display name
  Alt_FullName  STRING             -- Alternative name (e.g. in another language)
)
OPTIONS (description = 'Room and space catalogue dimension');


-- -----------------------------------------------------------------------------
-- DimReservation
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimReservation` (
  ReservationID  STRING     NOT NULL,  -- UUID
  Start_time     TIMESTAMP,            -- Reservation start datetime
  End_time       TIMESTAMP,            -- Reservation end datetime
  List_Item      STRING,               -- Booking list item reference
  Activity       STRING,               -- Type of activity
  Class          STRING,               -- Class or session type
  Department     STRING,               -- Owning department
  Professor      STRING,               -- Responsible person / professor
  ReservedBy     STRING                -- User who made the reservation
)
OPTIONS (description = 'Room reservation details dimension');


-- -----------------------------------------------------------------------------
-- DimConsumptionPrediction
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimConsumptionPrediction` (
  Cons_PredictionID  STRING  NOT NULL,  -- UUID
)
OPTIONS (description = 'Consumption forecast/prediction dimension');


-- -----------------------------------------------------------------------------
-- DimProductionPredictionPac
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimProductionPredictionPac` (
  Prod_PredictionID  STRING  NOT NULL,  -- UUID
  pred_date DATE NOT NULL,
  pred_hour INT64 NOT NULL,
  pred_sum_pac FLOAT64 NOT NULL,
  sum_pac INT64 NOT NULL
)
OPTIONS (description = 'Production forecast/prediction dimension');

-- -----------------------------------------------------------------------------
-- DimProductionPredictionDaysum
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimProductionPredictionDaysum` (
  Prod_PredictionID  STRING  NOT NULL,  -- UUID
  pred_date DATE NOT NULL,
  pred_hour INT64 NOT NULL,
  pred_daysum FLOAT64 NOT NULL,
  daysum INT64 NOT NULL
)
OPTIONS (description = 'Production forecast/prediction dimension');

-- =============================================================================
-- FACT TABLES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Power_FactTable
-- Grain: one row per inverter reading per time interval
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.Power_FactTable` (
  -- Surrogate PK
  FactID                       STRING  NOT NULL,  -- UUID generated at load time

  -- Foreign keys
  TimeID                       STRING  NOT NULL,  -- → DimTime.TimeID
  ConsumptionID                STRING  NOT NULL,  -- → DimConsumption.ConsumptionID
  InverterKey                  STRING  NOT NULL,  -- → DimInverter.InverterKey
  ErrorID                      STRING,            -- → DimErrors.ErrorID | NULL = no error

  -- Measures
  Prod_vs_Consumption_Diff     FLOAT64,           -- Production minus consumption (kWh)
  Total_Production_End_of_Day  FLOAT64,           -- Cumulative production at day end (kWh)
  Pct_Inverters_Running        FLOAT64,           -- % of inverters active (0–100)

  -- Partition column
  partition_date               DATE    NOT NULL   -- DATE(Year, Month, Day) from DimTime
)
PARTITION BY partition_date
OPTIONS (description = 'Power fact table: inverter production and energy consumption per time interval');


-- -----------------------------------------------------------------------------
-- Weather_FactTable
-- Grain: one row per weather observation per time interval
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.Weather_FactTable` (
  -- Surrogate PK
  FactID      STRING  NOT NULL,  -- UUID generated at load time

  -- Foreign keys
  TimeID      STRING  NOT NULL,  -- → DimTime.TimeID
  HumidityID  STRING  NOT NULL,  -- → DimHumidity.HumidityID
  ForecastID  STRING  NOT NULL,  -- → DimForecast.ForecastID
  TempID      STRING  NOT NULL,  -- → DimTemp.TempID

  -- Measures
  Most_Recent_Forecast  BOOL,     -- TRUE if this is the latest forecast for the slot
  Humidity_Today        FLOAT64,  -- Aggregated humidity for the day (%)
  Temp_Today            FLOAT64,  -- Aggregated temperature for the day (°C)

  -- Partition column
  partition_date        DATE    NOT NULL
)
PARTITION BY partition_date
OPTIONS (description = 'Weather fact table: observed humidity, temperature and forecast linkage per time interval');


-- -----------------------------------------------------------------------------
-- Rooms_FactTable
-- Grain: one row per room per time interval
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.Rooms_FactTable` (
  -- Surrogate PK
  FactID         STRING  NOT NULL,  -- UUID generated at load time

  -- Foreign keys
  TimeID         STRING  NOT NULL,  -- → DimTime.TimeID
  RoomID         INT64   NOT NULL,  -- → DimRoom.RoomID
  ReservationID  STRING,            -- → DimReservation.ReservationID | NULL = no booking

  -- Measures
  Pct_Rooms_Booked  FLOAT64,  -- % of rooms booked at this time slot (0–100)
  Rooms_Free_Count  INT64,    -- Number of rooms available at this time slot

  -- Partition column
  partition_date    DATE    NOT NULL
)
PARTITION BY partition_date
OPTIONS (description = 'Rooms fact table: room occupancy and reservation linkage per time interval');


-- -----------------------------------------------------------------------------
-- Prediction_FactTable
-- Grain: one row per prediction interval
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.Prediction_FactTable` (
  -- Surrogate PK
  FactID             STRING  NOT NULL,  -- UUID generated at load time

  -- Foreign keys
  TimeID             STRING  NOT NULL,  -- → DimTime.TimeID
  Cons_PredictionID  STRING  NOT NULL,  -- → DimConsumptionPrediction.Cons_PredictionID
  Prod_PredictionIDPac  STRING  NOT NULL,  -- → DimProductionPrediction.Prod_PredictionID
  Prod_PredictionIDDaysum STRING NOT NULL,

  -- Measures
  Predicted_ProductionPac   FLOAT64,  -- Forecast solar production for the interval (kWh)
  Predicted_ProductionDaysum  FLOAT64,

  Predicted_Consumption  FLOAT64,  -- Forecast energy consumption for the interval (kWh)

  -- Partition column
  partition_date         DATE    NOT NULL
)
PARTITION BY partition_date
OPTIONS (description = 'Prediction fact table: forecasted production and consumption per time interval');


-- =============================================================================
-- UNENFORCED PRIMARY & FOREIGN KEYS
-- =============================================================================

-- Dimension PKs
ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimTime`
  ADD PRIMARY KEY (TimeID) NOT ENFORCED;

ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimInverter`
  ADD PRIMARY KEY (InverterKey) NOT ENFORCED;

ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimConsumption`
  ADD PRIMARY KEY (ConsumptionID) NOT ENFORCED;

ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimErrors`
  ADD PRIMARY KEY (ErrorID) NOT ENFORCED;

ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimHumidity`
  ADD PRIMARY KEY (HumidityID) NOT ENFORCED;

ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimTemp`
  ADD PRIMARY KEY (TempID) NOT ENFORCED;

ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimForecast`
  ADD PRIMARY KEY (ForecastID) NOT ENFORCED;

ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimRoom`
  ADD PRIMARY KEY (RoomID) NOT ENFORCED;

ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimReservation`
  ADD PRIMARY KEY (ReservationID) NOT ENFORCED;

ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimConsumptionPrediction`
  ADD PRIMARY KEY (Cons_PredictionID) NOT ENFORCED;

ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimProductionPredictionPac`
  ADD PRIMARY KEY (Prod_PredictionID) NOT ENFORCED;

ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimProductionPredictionDaysum`
  ADD PRIMARY KEY (Prod_PredictionID) NOT ENFORCED;

-- Fact table PKs
ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.Power_FactTable`
  ADD PRIMARY KEY (FactID) NOT ENFORCED;

ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.Weather_FactTable`
  ADD PRIMARY KEY (FactID) NOT ENFORCED;

ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.Rooms_FactTable`
  ADD PRIMARY KEY (FactID) NOT ENFORCED;

ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.Prediction_FactTable`
  ADD PRIMARY KEY (FactID) NOT ENFORCED;

-- Fact table FKs
ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.Power_FactTable`
  ADD FOREIGN KEY (TimeID)        REFERENCES `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimTime`(TimeID)               NOT ENFORCED,
  ADD FOREIGN KEY (ConsumptionID) REFERENCES `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimConsumption`(ConsumptionID) NOT ENFORCED,
  ADD FOREIGN KEY (InverterKey)   REFERENCES `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimInverter`(InverterKey)      NOT ENFORCED,
  ADD FOREIGN KEY (ErrorID)       REFERENCES `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimErrors`(ErrorID)            NOT ENFORCED;

ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.Weather_FactTable`
  ADD FOREIGN KEY (TimeID)     REFERENCES `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimTime`(TimeID)         NOT ENFORCED,
  ADD FOREIGN KEY (HumidityID) REFERENCES `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimHumidity`(HumidityID) NOT ENFORCED,
  ADD FOREIGN KEY (ForecastID) REFERENCES `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimForecast`(ForecastID) NOT ENFORCED,
  ADD FOREIGN KEY (TempID)     REFERENCES `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimTemp`(TempID)         NOT ENFORCED;

ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.Rooms_FactTable`
  ADD FOREIGN KEY (TimeID)        REFERENCES `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimTime`(TimeID)               NOT ENFORCED,
  ADD FOREIGN KEY (RoomID)        REFERENCES `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimRoom`(RoomID)               NOT ENFORCED,
  ADD FOREIGN KEY (ReservationID) REFERENCES `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimReservation`(ReservationID) NOT ENFORCED;

ALTER TABLE `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.Prediction_FactTable`
  ADD FOREIGN KEY (TimeID)            REFERENCES `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimTime`(TimeID)                               NOT ENFORCED,
  ADD FOREIGN KEY (Cons_PredictionID) REFERENCES `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimConsumptionPrediction`(Cons_PredictionID)   NOT ENFORCED,
  ADD FOREIGN KEY (Prod_PredictionIDPac) REFERENCES `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimProductionPredictionPac`(Prod_PredictionID)    NOT ENFORCED,
  ADD FOREIGN KEY (Prod_PredictionIDDaysum) REFERENCES `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimProductionPredictionDaysum`(Prod_PredictionID)    NOT ENFORCED;