# AUTHORS: Rachel Spiegel and Sara Fatimah
# DATE: December 2022

# DESCRIPTION: This code performs a multi-criteria evaluation (MCE) analysis to identify which census tracts
# affected by the 2020 Santiam wildfire in Oregon are the most
# vulnerable, and thus should be targeted for aid. Variables include Oregon census tracts (shapefile), the Santiam wildfire perimeter (shapefile),
# census median age and median income data (CSV), hospital locations (shapefile), fire station locations (shapefile),
# burn severity (raster), and roads (shapefile).
#%%
# Import Arcpy and modules, set workspace
import arcpy
from arcpy.sa import *
from arcpy.da import *

base = r"S:\GEOG_6308_80_Programming_Geospatial_202203\Class-Shared\Fatimah_Spiegel\FinalProjectData\Data_Submit\Final_Data.gdb"
arcpy.env.workspace = base

arcpy.env.overwriteOutput = True
#%%
# Select census tracts by location, export new census tract shapefile that only includes those that intersect with wildfire perimeter

## Make a layer from the census tract shapefile
arcpy.management.MakeFeatureLayer(
    in_features="or_census_tract_final", out_layer="census_layer"
)

## Select by location where census tracts intersect wildfire perimeter
arcpy.management.SelectLayerByLocation(
    in_layer="census_layer",
    overlap_type="INTERSECT",
    select_features="wf_perimeter",
    selection_type="NEW_SELECTION",
)

# Get count to check number of census tracts (should be 13)
print(arcpy.GetCount_management(in_rows="census_layer"))
#%%
# Make selected census tracts a permanent layer
arcpy.management.CopyFeatures(in_features="census_layer", out_feature_class="census_wf")
#%%
# Join census data table (CSV) to census tract shapefile
census_tract_income = arcpy.management.AddJoin(
    in_layer_or_view="census_wf",
    in_field="ID",
    join_table="cen_data_or",
    join_field="ID",
)
#%%
# Copy layer to a new permanent feature class
arcpy.management.CopyFeatures(
    in_features=census_tract_income, out_feature_class="census_wf2"
)
#%%
# Select roads by location, export new roads shapefile that only includes those that intersect with the census tracts in our study area

## Make a layer from the roads shapefile
arcpy.management.MakeFeatureLayer(
    in_features="or_trans_network", out_layer="road_layer"
)

## Select by location where roads intersect with census tracts
arcpy.management.SelectLayerByLocation(
    in_layer="road_layer",
    overlap_type="INTERSECT",
    select_features="census_wf2",
    selection_type="NEW_SELECTION",
)

# Get count to check number of roads (should be roughly 52,000)
print(arcpy.GetCount_management(in_rows="road_layer"))
#%%
# Make selected roads a permanent layer
arcpy.management.CopyFeatures(in_features="road_layer", out_feature_class="road_cen")
#%%
# Summarize within to count number of roads in each census tract
arcpy.analysis.SummarizeWithin(
    in_polygons="census_wf2", in_sum_features="road_cen", out_feature_class="census_wf3"
)
#%%
# Select hospitals by location, export new hospital shapefile that only includes those that are within 5 miles of census tracts in our study area

## Make a layer from the hospital shapefile
arcpy.management.MakeFeatureLayer(
    in_features="or_accute_care_hosp", out_layer="hospital_layer"
)

arcpy.management.SelectLayerByLocation(
    in_layer="hospital_layer",
    overlap_type="WITHIN_A_DISTANCE",
    select_features="census_wf3",
    search_distance="5 Miles",
    selection_type="NEW_SELECTION",
)

# Get count to check number of hospitals (should be 4)
print(arcpy.GetCount_management(in_rows="hospital_layer"))
#%%
# Make selected hospitals its own feature class
arcpy.management.CopyFeatures(
    in_features="hospital_layer", out_feature_class="hospital_cen"
)
#%%
# Select fire stations by location, export new roads shapefile that only includes those that intersect with the census tracts in our study area

## Make a layer from the fire stations shapefile
arcpy.management.MakeFeatureLayer(
    in_features="or_fstations", out_layer="fstation_layer"
)

## Select by location where fire stations intersect with census tracts in study area
arcpy.management.SelectLayerByLocation(
    in_layer="fstation_layer",
    overlap_type="INTERSECT",
    select_features="census_wf3",
    selection_type="NEW_SELECTION",
)

# Get count to check number of fire stations (should be 39)
print(arcpy.GetCount_management(in_rows="fstation_layer"))
#%%
# Make selected fire stations its own feature class
arcpy.management.CopyFeatures(
    in_features="fstation_layer", out_feature_class="fstation_cen"
)
#%%
# Summarize within to count number of fire stations in each census tract
arcpy.analysis.SummarizeWithin(
    in_polygons="census_wf3",
    in_sum_features="fstation_cen",
    out_feature_class="census_wf4",
)
#%%
# Check out spatial extension
arcpy.CheckOutExtension("Spatial")

# Run Euclidean Distance for hospitals
outEucDistance = EucDistance(in_source_data="hospital_cen")

# Save the output
outEucDistance.save("h_distance")
#%%
# Use raster calculator to multiply hospital euclidean distance raster by itself
in_raster1 = "h_distance"
in_raster2 = "h_distance"

out_h_raster = RasterCalculator(
    rasters=[in_raster1, in_raster2], input_names=["x", "y"], expression="x*y"
)
#%%
# Save output
out_h_raster.save("h_distance_sq")
#%%
# Run Zonal Statistics as Table for hospital squared raster
outZonalStats = ZonalStatisticsAsTable(
    in_zone_data="census_wf4",
    zone_field="GEOID",
    in_value_raster="h_distance_sq",
    out_table="ZonalSt_hospital",
    ignore_nodata="DATA",
    statistics_type="MEAN",
)
#%%
# Join Zonal Statistics Table to census tracts shapefile
cen_zonal = arcpy.management.AddJoin(
    in_layer_or_view="census_wf4",
    in_field="OBJECTID",
    join_table="ZonalSt_hospital",
    join_field="OBJECTID",
)

arcpy.management.CopyFeatures(in_features=cen_zonal, out_feature_class="census_wf5")
#%%
# Run Zonal Statistics as Table for burn severity raster
outBurnZonSt = ZonalStatisticsAsTable(
    in_zone_data="census_wf5",
    zone_field="OBJECTID",
    in_value_raster="dnbr_final",
    out_table="ZonalSt_burn",
    ignore_nodata="DATA",
    statistics_type="MEAN",
)
#%%
# Change field name in burn Zonal Statistics table so it is distinguishable from the hospital field when joined
arcpy.management.AlterField(
    in_table="ZonalSt_burn",
    field="MEAN",
    new_field_name="MEAN_burn",
    new_field_alias="MEAN_burn",
)
#%%
# Join burn Zonal Statistics Table to census tracts shapefile
cen_zonal_burn = arcpy.management.AddJoin(
    in_layer_or_view="census_wf5",
    in_field="OBJECTID",
    join_table="ZonalSt_burn",
    join_field="OBJECTID",
)

arcpy.management.CopyFeatures(
    in_features=cen_zonal_burn, out_feature_class="census_wf6"
)
#%%
# Add fields to census tract shapefile for z-scores and scaled criteria

# Age Z-Score
arcpy.AddField_management(in_table="census_wf6", field_name="Z_age", field_type="FLOAT")

# Income z-score
arcpy.AddField_management(
    in_table="census_wf6", field_name="Z_income", field_type="FLOAT"
)

# Burn Severity z-score
arcpy.AddField_management(
    in_table="census_wf6", field_name="Z_burn", field_type="FLOAT"
)

# Roads z-score
arcpy.AddField_management(
    in_table="census_wf6", field_name="Z_road", field_type="FLOAT"
)

# Fire stations z-score
arcpy.AddField_management(
    in_table="census_wf6", field_name="Z_fstation", field_type="FLOAT"
)

# Age scaled
arcpy.AddField_management(
    in_table="census_wf6", field_name="age_scaled", field_type="FLOAT"
)

# Income scaled
arcpy.AddField_management(
    in_table="census_wf6", field_name="inc_scaled", field_type="FLOAT"
)

# Burn scaled
arcpy.AddField_management(
    in_table="census_wf6", field_name="burn_scaled", field_type="FLOAT"
)

# Roads scaled
arcpy.AddField_management(
    in_table="census_wf6", field_name="road_scaled", field_type="FLOAT"
)

# Fire stations scaled
arcpy.AddField_management(
    in_table="census_wf6", field_name="fstation_scaled", field_type="FLOAT"
)

# Hospitals scaled
arcpy.AddField_management(
    in_table="census_wf6", field_name="hos_scaled", field_type="FLOAT"
)
#%%
# Calculate mean and standard deviation for each z-score criteria, as well as min and max for hospitals (min/max scaling)

avgAge = ["census_wf5_census_wf4_cen_data_or_MEDIAN_AGE", "MEAN"]
stdAge = ["census_wf5_census_wf4_cen_data_or_MEDIAN_AGE", "STD"]

avgInc = ["census_wf5_census_wf4_cen_data_or_MEDIAN_INC", "MEAN"]
stdInc = ["census_wf5_census_wf4_cen_data_or_MEDIAN_INC", "STD"]

avgBurn = ["ZonalSt_burn_MEAN_burn", "MEAN"]
stdBurn = ["ZonalSt_burn_MEAN_burn", "STD"]

avgRoad = ["census_wf5_census_wf4_Polyline_Count", "MEAN"]
stdRoad = ["census_wf5_census_wf4_Polyline_Count", "STD"]

avgFstation = ["census_wf5_census_wf4_Point_Count", "MEAN"]
stdFstation = ["census_wf5_census_wf4_Point_Count", "STD"]

minHospital = ["census_wf5_ZonalSt_hospital_MEAN", "MIN"]
maxHospital = ["census_wf5_ZonalSt_hospital_MEAN", "MAX"]

arcpy.analysis.Statistics(
    in_table="census_wf6",
    out_table="cen_stats",
    statistics_fields=[
        avgAge,
        stdAge,
        avgInc,
        stdInc,
        avgBurn,
        stdBurn,
        avgRoad,
        stdRoad,
        avgFstation,
        stdFstation,
        minHospital,
        maxHospital,
    ],
)
#%%
# Set variables equal to the numbers calculated in the statistics table
# Age average
with arcpy.da.SearchCursor(
    in_table="cen_stats",
    field_names="MEAN_census_wf5_census_wf4_cen_data_or_MEDIAN_AGE",
) as rows:
    for row in rows:
        avgAgeNum = row

AgeAvg = float(".".join(str(elem) for elem in avgAgeNum))

# Should be 44.13
print(AgeAvg)
#%%
# Age standard deviation
with arcpy.da.SearchCursor(
    in_table="cen_stats", field_names="STD_census_wf5_census_wf4_cen_data_or_MEDIAN_AGE"
) as rows:
    for row in rows:
        stdAgeNum = row

AgeSTD = float(".".join(str(elem) for elem in stdAgeNum))

# Should be 10.05
print(AgeSTD)
#%%
# Income average
with arcpy.da.SearchCursor(
    in_table="cen_stats",
    field_names="MEAN_census_wf5_census_wf4_cen_data_or_MEDIAN_INC",
) as rows:
    for row in rows:
        avgIncNum = row

IncAvg = float(".".join(str(elem) for elem in avgIncNum))

# Should be 63191.85
print(IncAvg)
#%%
# Income standard deviation
with arcpy.da.SearchCursor(
    in_table="cen_stats", field_names="STD_census_wf5_census_wf4_cen_data_or_MEDIAN_INC"
) as rows:
    for row in rows:
        stdIncNum = row

IncSTD = float(".".join(str(elem) for elem in stdIncNum))

# Should be 13802.13
print(IncSTD)
#%%
# Burn average
with arcpy.da.SearchCursor(
    in_table="cen_stats", field_names="MEAN_ZonalSt_burn_MEAN_burn"
) as rows:
    for row in rows:
        avgBurnNum = row

BurnAvg = float(".".join(str(elem) for elem in avgBurnNum))

# Should be 0.047
print(BurnAvg)
#%%
# Burn standard deviation
with arcpy.da.SearchCursor(
    in_table="cen_stats", field_names="STD_ZonalSt_burn_MEAN_burn"
) as rows:
    for row in rows:
        stdBurnNum = row

BurnSTD = float(".".join(str(elem) for elem in stdBurnNum))

# Should be 0.125
print(BurnSTD)
#%%
# Roads average
with arcpy.da.SearchCursor(
    in_table="cen_stats", field_names="MEAN_census_wf5_census_wf4_Polyline_Count"
) as rows:
    for row in rows:
        avgRoadNum = row

RoadAvg = float(".".join(str(elem) for elem in avgRoadNum))

# Should be 4005.84
print(RoadAvg)
#%%
# Roads standard deviation
with arcpy.da.SearchCursor(
    in_table="cen_stats", field_names="STD_census_wf5_census_wf4_Polyline_Count"
) as rows:
    for row in rows:
        stdRoadNum = row

RoadSTD = float(".".join(str(elem) for elem in stdRoadNum))

# should be 3695.92
print(RoadSTD)
#%%
# Fire stations average
with arcpy.da.SearchCursor(
    in_table="cen_stats", field_names="MEAN_census_wf5_census_wf4_Point_Count"
) as rows:
    for row in rows:
        avgFstationNum = row

FstationAvg = float(".".join(str(elem) for elem in avgFstationNum))

# Should be 3
print(FstationAvg)
#%%
# Fire stations standard deviation
with arcpy.da.SearchCursor(
    in_table="cen_stats", field_names="STD_census_wf5_census_wf4_Point_Count"
) as rows:
    for row in rows:
        stdFstationNum = row

FstationSTD = float(".".join(str(elem) for elem in stdFstationNum))

# Should be 2.85
print(FstationSTD)
#%%
# Hospitals minimum value
with arcpy.da.SearchCursor(
    in_table="cen_stats", field_names="MIN_census_wf5_ZonalSt_hospital_MEAN"
) as rows:
    for row in rows:
        minHospitalNum = row

HospitalMin = float(".".join(str(elem) for elem in minHospitalNum))

# Should be 679320147.18
print(HospitalMin)
#%%
# Hospitals maximum value
with arcpy.da.SearchCursor(
    in_table="cen_stats", field_names="MAX_census_wf5_ZonalSt_hospital_MEAN"
) as rows:
    for row in rows:
        maxHospitalNum = row

HospitalMax = float(".".join(str(elem) for elem in maxHospitalNum))

# Should be 41248845252.58
print(HospitalMax)
#%%
# Calculate Z-score and populate attribute table

fields = [
    "census_wf5_census_wf4_cen_data_or_MEDIAN_INC",
    "census_wf5_census_wf4_cen_data_or_MEDIAN_AGE",
    "census_wf5_census_wf4_Polyline_Count",
    "census_wf5_census_wf4_Point_Count",
    "ZonalSt_burn_MEAN_burn",
    "Z_age",
    "Z_income",
    "Z_burn",
    "Z_road",
    "Z_fstation",
]

with arcpy.da.UpdateCursor(in_table="census_wf6", field_names=fields) as cursor:
    for row in cursor:
        row[5] = (row[1] - AgeAvg) / AgeSTD
        row[6] = (row[0] - IncAvg) / IncSTD
        row[7] = (row[4] - BurnAvg) / BurnSTD
        row[8] = (row[2] - RoadAvg) / RoadSTD
        row[9] = (row[3] - FstationAvg) / FstationSTD
        cursor.updateRow(row)
#%%
# Calculate scaled criteria for those that have z-score (all but hospital) and are more vulnerable with higher z-score

# age_scaled
z_fields_age = ["z_age", "age_scaled"]

with arcpy.da.UpdateCursor(in_table="census_wf6", field_names=z_fields_age) as cursor:
    for row in cursor:
        if row[0] <= -1.5:
            row[1] = 0.1
        elif (row[0] > -1.5) and (row[0] <= -1):
            row[1] = 0.2
        elif (row[0] > -1) and (row[0] <= -0.5):
            row[1] = 0.3
        elif (row[0] > -0.5) and (row[0] <= 0.5):
            row[1] = 0.5
        elif (row[0] > 0.5) and (row[0] <= 1):
            row[1] = 0.7
        elif (row[0] > 1) and (row[0] <= 1.5):
            row[1] = 0.85
        else:
            row[1] = 1
        cursor.updateRow(row)

# burn_scaled
z_fields_burn = ["z_burn", "burn_scaled"]

with arcpy.da.UpdateCursor(in_table="census_wf6", field_names=z_fields_burn) as cursor:
    for row in cursor:
        if row[0] <= -1.5:
            row[1] = 0.1
        elif (row[0] > -1.5) and (row[0] <= -1):
            row[1] = 0.2
        elif (row[0] > -1) and (row[0] <= -0.5):
            row[1] = 0.3
        elif (row[0] > -0.5) and (row[0] <= 0.5):
            row[1] = 0.5
        elif (row[0] > 0.5) and (row[0] <= 1):
            row[1] = 0.7
        elif (row[0] > 1) and (row[0] <= 1.5):
            row[1] = 0.85
        else:
            row[1] = 1
        cursor.updateRow(row)
#%%
# Calculate scaled criteria for those that have z-score (all but hospital) and are more vulnerable with lower z-score

# income_scaled
z_fields_inc = ["Z_income", "inc_scaled"]

with arcpy.da.UpdateCursor(in_table="census_wf6", field_names=z_fields_inc) as cursor:
    for row in cursor:
        if row[0] <= -1.5:
            row[1] = 1
        elif (row[0] > -1.5) and (row[0] <= -1):
            row[1] = 0.85
        elif (row[0] > -1) and (row[0] <= -0.5):
            row[1] = 0.7
        elif (row[0] > -0.5) and (row[0] <= 0.5):
            row[1] = 0.5
        elif (row[0] > 0.5) and (row[0] <= 1):
            row[1] = 0.3
        elif (row[0] > 1) and (row[0] <= 1.5):
            row[1] = 0.2
        else:
            row[1] = 0.1
        cursor.updateRow(row)

# road_scaled
z_fields_road = ["Z_road", "road_scaled"]

with arcpy.da.UpdateCursor(in_table="census_wf6", field_names=z_fields_road) as cursor:
    for row in cursor:
        if row[0] <= -1.5:
            row[1] = 1
        elif (row[0] > -1.5) and (row[0] <= -1):
            row[1] = 0.85
        elif (row[0] > -1) and (row[0] <= -0.5):
            row[1] = 0.7
        elif (row[0] > -0.5) and (row[0] <= 0.5):
            row[1] = 0.5
        elif (row[0] > 0.5) and (row[0] <= 1):
            row[1] = 0.3
        elif (row[0] > 1) and (row[0] <= 1.5):
            row[1] = 0.2
        else:
            row[1] = 0.1
        cursor.updateRow(row)

# Fire Stations scaled
z_fields_fstation = ["Z_fstation", "fstation_scaled"]

with arcpy.da.UpdateCursor(
    in_table="census_wf6", field_names=z_fields_fstation
) as cursor:
    for row in cursor:
        if row[0] <= -1.5:
            row[1] = 1
        elif (row[0] > -1.5) and (row[0] <= -1):
            row[1] = 0.85
        elif (row[0] > -1) and (row[0] <= -0.5):
            row[1] = 0.7
        elif (row[0] > -0.5) and (row[0] <= 0.5):
            row[1] = 0.5
        elif (row[0] > 0.5) and (row[0] <= 1):
            row[1] = 0.3
        elif (row[0] > 1) and (row[0] <= 1.5):
            row[1] = 0.2
        else:
            row[1] = 0.1
        cursor.updateRow(row)
#%%
# Calculate scaled hospital column using min/max scaling

hos_fields = ["census_wf5_ZonalSt_hospital_MEAN", "hos_scaled"]

with arcpy.da.UpdateCursor(in_table="census_wf6", field_names=hos_fields) as cursor:
    for row in cursor:
        row[1] = (row[0] - HospitalMin) / (HospitalMax - HospitalMin)
        cursor.updateRow(row)
#%%
# Add field for MCE calculation
arcpy.management.AddField(in_table="census_wf6", field_name="MCE", field_type="FLOAT")
#%%
# Calculate MCE and populate MCE field

MCE_fields = [
    "age_scaled",
    "inc_scaled",
    "burn_scaled",
    "road_scaled",
    "fstation_scaled",
    "hos_scaled",
    "MCE",
]

with arcpy.da.UpdateCursor(in_table="census_wf6", field_names=MCE_fields) as cursor:
    for row in cursor:
        row[6] = (
            (row[0] * 0.05)
            + (row[1] * 0.1)
            + (row[2] * 0.4)
            + (row[3] * 0.15)
            + (row[4] * 0.2)
            + (row[5] * 0.1)
        )
        cursor.updateRow(row)
#%%
## The above step is the final step of the code. This cell serves to delete all outputs in order to run the code again, and is thus commented out.

# arcpy.management.Delete(["cen_stats",
#                        "census_wf",
#                       "census_wf2",
#                        "census_wf3",
#                        "census_wf4",
#                        "census_wf5",
#                        "census_wf6",
#                        "fstation_cen",
#                        "h_distance",
#                       "h_distance_sq",
#                        "hospital_cen",
#                       "road_cen",
#                       "ZonalSt_burn",
#                       "ZonalSt_hospital"])
# %%