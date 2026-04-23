SELECT 
  -- Fact Measures
  f.FactID,
  f.partition_date,
  f.Prod_vs_Consumption_Diff,
  f.Total_Production_End_of_Day,
  f.Total_Consumption_End_of_day,
  f.Pct_Inverters_Running,

  -- Time Dim
  t.Year,
  t.Month,
  t.Day,
  t.Hour,
  
  -- Inverter Dim
  i.InverterID as Inverter_Business_Key,
  i.Status as Inverter_Status,
  i.PAC,
  i.Daysum,
  
  -- Consumption Dim
  c.Value as Consumption_Value,
  c.Variation as Consumption_Variation,
  
  -- Error Dim
  e.Error_info

FROM `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.Power_FactTable` AS f
LEFT JOIN `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimTime` AS t 
  ON f.TimeID = t.TimeID
LEFT JOIN `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimInverter` AS i 
  ON f.InverterKey = i.InverterKey
LEFT JOIN `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimConsumption` AS c 
  ON f.ConsumptionID = c.ConsumptionID
LEFT JOIN `project-d31bc18d-8d9f-48db-a77.DataCycle_Warehouse.DimErrors` AS e 
  ON f.ErrorID = e.ErrorID