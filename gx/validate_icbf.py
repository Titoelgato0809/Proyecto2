from pathlib import Path
import sys

import pandas as pd
import great_expectations as gx



# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

def validations_spotify():
    
    
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DATA_PATH = (
        PROJECT_ROOT
        / "data"
        / "raw"
        / "DatasetCompleto.csv"
    )

    # ---------------------------------------------------------
    # Load the Spotify Applications dataset
    # ---------------------------------------------------------

    df = pd.read_csv(
        DATA_PATH,
        sep=","
    )

    print("Dataset shape:", df.shape)


    # ---------------------------------------------------------
    # Create the Great Expectations Data Context
    # ---------------------------------------------------------

    context = gx.get_context(
        mode="ephemeral"
    )

    print("GX Data Context created successfully.")
    print("Context type:", type(context).__name__)

    # ---------------------------------------------------------
    # Create the Pandas Data Source
    # ---------------------------------------------------------

    data_source = context.data_sources.add_pandas(
        name="ICBF_pandas_source"
    )

    print("Pandas Data Source created successfully.")
    print("Data Source name:", data_source.name)

    # ---------------------------------------------------------
    # Create the Data Asset
    # ---------------------------------------------------------

    data_asset = data_source.add_dataframe_asset(
        name="ICBF_applications"
    )

    print("Data Asset created successfully.")
    print("Data Asset name:", data_asset.name)

    # ---------------------------------------------------------
    # Create the Batch Definition
    # ---------------------------------------------------------

    batch_definition = data_asset.add_batch_definition_whole_dataframe(
        name="whole_icbf_dataframe"
    )

    print("Batch Definition created successfully.")
    print("Batch Definition name:", batch_definition.name)

    # ---------------------------------------------------------
    # Create the Batch
    # ---------------------------------------------------------

    batch_parameters = {
        "dataframe": df
    }

    batch = batch_definition.get_batch(
        batch_parameters=batch_parameters
    )

    print("Batch created successfully.")
    print("Batch type:", type(batch).__name__)

    # ---------------------------------------------------------
    # Step 12- Define and Test the First Expectation
    # Codigo Departamento UDS 
    # ---------------------------------------------------------

    icbf_suite = context.suites.add_or_update(
        gx.ExpectationSuite(name="icbf_suite")
    )

    Codigo_Departamento_UDS_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
        column="Codigo Departamento UDS",
        mostly=0.98,
        severity="critical",
    )
    icbf_suite.add_expectation(Codigo_Departamento_UDS_expectation)
    
    # ---------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Codigo Municipio UDS
    # ---------------------------------------------------------

    Codigo_Municipio_UDS_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
    column= "Codigo Municipio UDS",
    mostly=0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Codigo_Municipio_UDS_expectation)
    
    # ---------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Codigo CentroZonal UDS
    # ---------------------------------------------------------

    Codigo_CentroZonal_UDS_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
    column= "Codigo CentroZonal UDS",
    mostly=0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Codigo_CentroZonal_UDS_expectation)
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Codigo Unidad Servicio
    # ---------------------------------------------------------

    Codigo_Unidad_Servicio_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
    column= "Codigo Unidad Servicio",
    mostly = 0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Codigo_Unidad_Servicio_expectation)
    
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Codigo Unidad Servicio
    # ---------------------------------------------------------

    Codigo_Unidad_Servicio_U_expectation = gx.expectations.ExpectColumnValuesToBeBetween(
    column= "Codigo Unidad Servicio",
    min = 0,
    mostly = 1,
    severity= "critical"
    )
    icbf_suite.add_expectation(Codigo_Unidad_Servicio_expectation)
    
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Codigo Unidad Servicio
    # ---------------------------------------------------------

    Codigo_Unidad_Servicio_U_expectation = gx.expectations.ExpectColumnValuesToBeBetween(
    column= "Codigo Unidad Servicio",
    min = 0,
    mostly = 1,
    severity= "critical"
    )
    icbf_suite.add_expectation(Codigo_Unidad_Servicio_U_expectation)
    
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Codigo Municipio UDS
    # ---------------------------------------------------------

    Codigo_Municipio_U_UDS_expectation = gx.expectations.ExpectColumnValuesToBeBetween(
    column= "Codigo Municipio UDS",
    min = 0,
    mostly =1,
    severity= "critical"
    )
    icbf_suite.add_expectation(Codigo_Municipio_U_UDS_expectation)
    
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Codigo Municipio UDS
    # ---------------------------------------------------------

    Codigo_Departamento_U_UDS_expectation = gx.expectations.ExpectColumnValuesToBeBetween(
    column= "Codigo Departamento UDS",
    min = 0,
    mostly = 1,
    severity= "critical"
    )
    icbf_suite.add_expectation(Codigo_Departamento_U_UDS_expectation)
    
    # ---------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Codigo Municipio UDS
    # ---------------------------------------------------------

    Codigo_Municipio_UDS_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
    column= "Codigo Municipio UDS",
    mostly=0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Codigo_Municipio_UDS_expectation)
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Centro Zonal UDS
    # ---------------------------------------------------------

    Centro_Zonal_UDS_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
    column= "Centro Zonal UDS",
    mostly = 0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Centro_Zonal_UDS_expectation)
    
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Municipio UDS
    # ---------------------------------------------------------

    Municipio_UDS_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
    column= "Municipio UDS",
    mostly = 0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Municipio_UDS_expectation)
    
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Departamento UDS
    # ---------------------------------------------------------

    Departamento_UDS_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
    column= "Departamento UDS",
    mostly = 0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Departamento_UDS_expectation)
    
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Grupo Etnico
    # ---------------------------------------------------------

    Grupo_Etnico_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
    column= "Grupo Etnico",
    mostly = 0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Grupo_Etnico_expectation)
    
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Rango Edad
    # ---------------------------------------------------------

    Rango_Edad_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
    column= "Rango Edad",
    mostly = 0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Rango_Edad_expectation)
    
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Rango Edad
    # ---------------------------------------------------------

    Nombre_Servicio_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
    column= "Nombre Servicio",
    mostly = 0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Nombre_Servicio_expectation)
    
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Rango Edad
    # ---------------------------------------------------------

    Tipo_Beneficiario_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
    column= "Tipo de Beneficiario",
    mostly = 0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Tipo_Beneficiario_expectation)
    
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Rango Edad
    # ---------------------------------------------------------

    Beneficiarios_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
    column= "Beneficiarios",
    mostly = 0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Beneficiarios_expectation)
    
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Rango Edad
    # ---------------------------------------------------------

    Beneficiarios_U_expectation = gx.expectations.ExpectColumnValuesToBeBetween(
    column= "Beneficiarios",
    min=0,
    mostly = 0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Beneficiarios_U_expectation)
    
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Rango Edad
    # ---------------------------------------------------------

    Beneficiarios_U_expectation = gx.expectations.ExpectColumnValuesToBeBetween(
    column= "Beneficiarios",
    min=0,
    mostly = 0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Beneficiarios_U_expectation)
    
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Rango Edad
    # ---------------------------------------------------------

    Sexo_expectation = gx.expectations.ExpectColumnValuesToBeInSet(
    column= "Sexo",
    value_set=[M,H,I]
    mostly = 0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Sexo_expectation)
  
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Estado Atención
    # ---------------------------------------------------------

    Estado_Atención_expectation = gx.expectations.ExpectColumnValuesToBeInSet(
    column= "Estado Atención",
    value_set=[1,2,A,I]
    mostly = 0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Estado_Atención_expectation)
    
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Estado Atención
    # ---------------------------------------------------------

    Zona_Ubicacion_Beneficiario_expectation = gx.expectations.ExpectColumnValuesToBeInSet(
    column= "Zona Ubicacion Beneficiario",
    value_set=["CABECERA","RESTO"]
    mostly = 0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Zona_Ubicacion_Beneficiario_expectation)
    
    # --------------------------------------------------------
    # Step 12- Define and Test the Second Expectation
    # Estado Atención
    # ---------------------------------------------------------

    Presenta_Discapacidad_expectation = gx.expectations.ExpectColumnValuesToBeInSet(
    column= "Presenta Discapacidad",
    value_set=["CABECERA","RESTO"]
    mostly = 0.98,
    severity= "critical"
    )
    icbf_suite.add_expectation(Presenta_Discapacidad_expectation)
    
    #=========================================================
    # [PRUEBA CONTROLADA DE ERRORES SPOTIFY - DESCOMENTAR PARA PROBAR]
    # =========================================================
    df_bad_spotify = df.copy()
    # # Inyectar valores nulos en track_id (Falla Critical)
    df_bad_spotify.loc[df_bad_spotify.index[:50], "track_id"] = None
    # # Inyectar energía fuera de rango (Falla Critical)
    df_bad_spotify.loc[df_bad_spotify.index[:50], "energy"] = 99.0
    #
    bad_spotify_result = validation_definition.run(
         batch_parameters={"dataframe": df_bad_spotify},
         result_format={"result_format": "SUMMARY"}
     )
    print("\n--- [PRUEBA CONTROLADA SPOTIFY] ---")
    print("Éxito de la validación con datos corruptos:", bad_spotify_result.success)
    # =========================================================
    

    # ---------------------------------------------------------
    # Step 16 — Run the Validation Definition
    # ---------------------------------------------------------

    validation_result = validation_definition.run(
        batch_parameters={
            "dataframe": df
        },
        result_format={
            "result_format": "SUMMARY"
        },
    )

    print("Validation executed successfully.")

    print(
        "Overall validation success:",
        validation_result.success,
    )
    

    # ---------------------------------------------------------
    # Step 17 — Inspect the Validation Results
    # ---------------------------------------------------------

    print("\nValidation Summary")
    print("------------------")
    print(
        "Overall success:",
        validation_result.success,
    )
    print(
        "Expectations evaluated:",
        len(validation_result.results),
    )

    for result in validation_result.results:
        expectation = result.expectation

        print("\nExpectation:", type(expectation).__name__)
        print("Column:", getattr(expectation, "column", None))
        print("Severity:", expectation.severity)
        print("Success:", result.success)
        print(
            "Unexpected count:",
            result.result.get("unexpected_count", 0),
        )
        print(
            "Unexpected percent:",
            result.result.get("unexpected_percent", 0),
        )
    # ---------------------------------------------------------
    # Step 20 — Create and Register the Checkpoint
    # ---------------------------------------------------------

    new_checkpoint = gx.Checkpoint(
        name="beneficiarios_validation_checkpoint",
        validation_definitions=[
            validation_definition
        ],
        actions=[],
        result_format={
            "result_format": "SUMMARY"
        },
    )

    checkpoint = context.checkpoints.add(
        new_checkpoint
    )

    print("Checkpoint created successfully.")
    print("Checkpoint name:", checkpoint.name)

    # ---------------------------------------------------------
    # Step 21 — Run the Checkpoint
    # ---------------------------------------------------------

    checkpoint_result = checkpoint.run(
        batch_parameters={
            "dataframe": df
        }
    )

    print("Checkpoint executed successfully.")
    print(
        "Checkpoint success:",
        checkpoint_result.success,
    )
