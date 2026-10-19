from pathlib import Path
import sys

import pandas as pd
import great_expectations as gx


# ---------------------------------------------------------
# Project paths & Imports
# ---------------------------------------------------------

def validations_sisben():
    
    PROJECT_ROOT = Path(__file__).resolve().parent

    # Agregar la raíz al sys.path para importar desde src
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.append(str(PROJECT_ROOT))
        
    from src.extract_sisben import extract_sisben_data

    # ---------------------------------------------------------
    # Load the Sisben Applications dataset
    # ---------------------------------------------------------
    df_sisben = extract_sisben_data()
    
    print("Dataset shape:", df_sisben.shape)

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
        name="Sisben_pandas_source"
    )

    print("Pandas Data Source created successfully.")
    print("Data Source name:", data_source.name)

    # ---------------------------------------------------------
    # Create the Data Asset
    # ---------------------------------------------------------

    data_asset = data_source.add_dataframe_asset(
        name="Sisben_applications"
    )

    print("Data Asset created successfully.")
    print("Data Asset name:", data_asset.name)

    # ---------------------------------------------------------
    # Create the Batch Definition
    # ---------------------------------------------------------

    batch_definition = data_asset.add_batch_definition_whole_dataframe(
        name="whole_Sisben_dataframe"
    )

    print("Batch Definition created successfully.")
    print("Batch Definition name:", batch_definition.name)

    # ---------------------------------------------------------
    # Create the Batch
    # ---------------------------------------------------------

    batch_parameters = {
        "dataframe": df_sisben
    }

    batch = batch_definition.get_batch(
        batch_parameters=batch_parameters
    )

    print("Batch created successfully.")
    print("Batch type:", type(batch).__name__)

    # ---------------------------------------------------------
    # Step 12 — Define and Add Expectations to Suite
    # ---------------------------------------------------------

    sisben_suite = context.suites.add_or_update(
        gx.ExpectationSuite(name="sisben_suite")
    )

    # Codigo Municipio (Not Null)
    Codigo_municipio_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
        column="cod_mpio",
        mostly=0.98,
        severity="critical",
    )
    sisben_suite.add_expectation(Codigo_municipio_expectation)
    
    # Codigo Municipio (Mayor o igual a 0)
    Codigo_municipio_U_expectation = gx.expectations.ExpectColumnValuesToBeBetween(
        column="cod_mpio",
        min_value=0,
        mostly=0.98,
        severity="critical",
    )
    sisben_suite.add_expectation(Codigo_municipio_U_expectation)
    
    # Zona (1: Cabecera, 2: Resto/Rural)
    Zona_expectation = gx.expectations.ExpectColumnValuesToBeInSet(
        column="zona",
        value_set=["1", "2", 1, 2],
        mostly=0.98,
        severity="warning",
    )
    sisben_suite.add_expectation(Zona_expectation)
    
    # Grupo Sisben (A, B, C, D)
    Grupo_expectation = gx.expectations.ExpectColumnValuesToBeInSet(
        column="grupo", 
        value_set=["A", "B", "C", "D"],
        mostly=0.98,
        severity="warning",
    )
    sisben_suite.add_expectation(Grupo_expectation)
    
    # Factor de Expansión (fex >= 0)
    Fex_expectation = gx.expectations.ExpectColumnValuesToBeBetween(
        column="fex",
        min_value=0,
        mostly=1.0,
        severity="critical",
    )
    sisben_suite.add_expectation(Fex_expectation) 
    
    # Factor de Expansión (Not Null)
    Fex_U_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
        column="fex",
        mostly=0.95,
        severity="warning",
    )
    sisben_suite.add_expectation(Fex_U_expectation) 

    # ---------------------------------------------------------
    # Step 15 — Create and Register Validation Definition
    # ---------------------------------------------------------

    validation_definition = context.validation_definitions.add(
        gx.ValidationDefinition(
            name="sisben_validation_definition",
            data=batch_definition,
            suite=sisben_suite,
        )
    )

    print("Validation Definition created successfully.")

    # ---------------------------------------------------------
    # Step 16 — Run the Validation Definition
    # ---------------------------------------------------------

    validation_result = validation_definition.run(
        batch_parameters={
            "dataframe": df_sisben
        },
        result_format={
            "result_format": "SUMMARY"
        },
    )

    print("Validation executed successfully.")
    print("Overall validation success:", validation_result.success)

    # ---------------------------------------------------------
    # Step 17 — Inspect the Validation Results
    # ---------------------------------------------------------

    print("\nValidation Summary")
    print("------------------")
    print("Overall success:", validation_result.success)
    print("Expectations evaluated:", len(validation_result.results))

    for result in validation_result.results:
        expectation = result.expectation

        print("\nExpectation:", type(expectation).__name__)
        print("Column:", getattr(expectation, "column", None))
        print("Severity:", getattr(expectation, "severity", "N/A"))
        print("Success:", result.success)
        print("Unexpected count:", result.result.get("unexpected_count", 0))
        print("Unexpected percent:", result.result.get("unexpected_percent", 0))

    # ---------------------------------------------------------
    # Step 20 — Create and Register the Checkpoint
    # ---------------------------------------------------------

    new_checkpoint = gx.Checkpoint(
        name="sisben_validation_checkpoint",
        validation_definitions=[validation_definition],
        actions=[],
        result_format={"result_format": "SUMMARY"},
    )

    checkpoint = context.checkpoints.add(new_checkpoint)

    print("Checkpoint created successfully.")
    print("Checkpoint name:", checkpoint.name)

    # ---------------------------------------------------------
    # Step 21 — Run the Checkpoint
    # ---------------------------------------------------------

    checkpoint_result = checkpoint.run(
        batch_parameters={"dataframe": df_sisben}
    )

    print("Checkpoint executed successfully.")
    print("Checkpoint success:", checkpoint_result.success)


if __name__ == "__main__":
    validations_sisben()  # <-- Corregido: antes llamaba a validations_icbf()