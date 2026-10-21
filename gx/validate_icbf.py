from pathlib import Path
import sys

import pandas as pd
import great_expectations as gx


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

def validations_icbf():
    
        PROJECT_ROOT = Path(__file__).resolve().parent.parent
        DATA_PATH = (
            PROJECT_ROOT
            / "data"
            / "raw"
            / "DatasetCompleto.csv"
        )

        # ---------------------------------------------------------
        # Load the ICBF Applications dataset
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
        # Step 12 — Define and Add Expectations to Suite
        # ---------------------------------------------------------

        icbf_suite = context.suites.add_or_update(
            gx.ExpectationSuite(name="icbf_suite")
        )

        # Codigo Departamento UDS 
        Codigo_Departamento_UDS_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
            column="Codigo Departamento UDS",
            mostly=1.0,
            severity="critical",
        )
        icbf_suite.add_expectation(Codigo_Departamento_UDS_expectation)
        
        # Codigo Municipio UDS
        Codigo_Municipio_UDS_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
            column="Codigo Municipio UDS",
            mostly=1.0,
            severity="critical",
        )
        icbf_suite.add_expectation(Codigo_Municipio_UDS_expectation)
        
        # Codigo CentroZonal UDS
        Codigo_CentroZonal_UDS_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
            column="Codigo CentroZonal UDS",
            mostly=1.0,
            severity="critical",
        )
        icbf_suite.add_expectation(Codigo_CentroZonal_UDS_expectation)

        # Codigo Unidad Servicio
        Codigo_Unidad_Servicio_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
            column="Codigo Unidad Servicio",
            mostly=1.0,
            severity="critical",
        )
        icbf_suite.add_expectation(Codigo_Unidad_Servicio_expectation)

        # Codigo Unidad Servicio (No Negativo)
        Codigo_Unidad_Servicio_U_expectation = gx.expectations.ExpectColumnValuesToBeBetween(
            column="Codigo Unidad Servicio",
            min_value=0,
            mostly=1.0,
            severity="critical",
        )
        icbf_suite.add_expectation(Codigo_Unidad_Servicio_U_expectation)

        # Codigo Municipio UDS (No Negativo)
        Codigo_Municipio_U_UDS_expectation = gx.expectations.ExpectColumnValuesToBeBetween(
            column="Codigo Municipio UDS",
            min_value=0,
            mostly=1.0,
            severity="critical",
        )
        icbf_suite.add_expectation(Codigo_Municipio_U_UDS_expectation)

        # Codigo Departamento UDS (No Negativo)
        Codigo_Departamento_U_UDS_expectation = gx.expectations.ExpectColumnValuesToBeBetween(
            column="Codigo Departamento UDS",
            min_value=0,
            mostly=1.0,
            severity="critical",
        )
        icbf_suite.add_expectation(Codigo_Departamento_U_UDS_expectation)

        # Centro Zonal UDS
        Centro_Zonal_UDS_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
            column="Centro Zonal UDS",
            mostly=1.0,
            severity="critical",
        )
        icbf_suite.add_expectation(Centro_Zonal_UDS_expectation)

        # Municipio UDS
        Municipio_UDS_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
            column="Municipio UDS",
            mostly=0.98,
            severity="critical",
        )
        icbf_suite.add_expectation(Municipio_UDS_expectation)

        # Departamento UDS
        Departamento_UDS_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
            column="Departamento UDS",
            mostly=0.98,
            severity="critical",
        )
        icbf_suite.add_expectation(Departamento_UDS_expectation)

        # Grupo Etnico
        Grupo_Etnico_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
            column="Grupo Etnico",
            mostly=0.98,
            severity="critical",
        )
        icbf_suite.add_expectation(Grupo_Etnico_expectation)

        # Rango Edad
        Rango_Edad_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
            column="Rango Edad",
            mostly=0.98,
            severity="critical",
        )
        icbf_suite.add_expectation(Rango_Edad_expectation)

        # Nombre Servicio
        Nombre_Servicio_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
            column="Nombre Servicio",
            mostly=0.98,
            severity="critical",
        )
        icbf_suite.add_expectation(Nombre_Servicio_expectation)

        # Tipo Beneficiario
        Tipo_Beneficiario_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
            column="Tipo de Beneficiario",
            mostly=0.98,
            severity="critical",
        )
        icbf_suite.add_expectation(Tipo_Beneficiario_expectation)

        # Beneficiarios (Not Null)
        Beneficiarios_expectation = gx.expectations.ExpectColumnValuesToNotBeNull(
            column="Beneficiarios",
            mostly=1.0,
            severity="warning",
        )
        icbf_suite.add_expectation(Beneficiarios_expectation)

        # Beneficiarios (No Negativo)
        Beneficiarios_U_expectation = gx.expectations.ExpectColumnValuesToBeBetween(
            column="Beneficiarios",
            min_value=0,
            mostly=1.0,
            severity="critical",
        )
        icbf_suite.add_expectation(Beneficiarios_U_expectation)

        # Sexo
        Sexo_expectation = gx.expectations.ExpectColumnValuesToBeInSet(
            column="Sexo",
            value_set=["M", "H", "I"],
            mostly=0.98,
            severity="critical",
        )
        icbf_suite.add_expectation(Sexo_expectation)

        # Estado Atención
        Estado_Atención_expectation = gx.expectations.ExpectColumnValuesToBeInSet(
            column="Estado Atención",
            value_set=["1", "2", "A", "I"],
            mostly=0.95,
            severity="critical",
        )
        icbf_suite.add_expectation(Estado_Atención_expectation)

        # Zona Ubicacion Beneficiario
        Zona_Ubicacion_Beneficiario_expectation = gx.expectations.ExpectColumnValuesToBeInSet(
            column="Zona Ubicacion Beneficiario",
            value_set=["CABECERA", "RESTO"],
            mostly=0.98,
            severity="critical",
        )
        icbf_suite.add_expectation(Zona_Ubicacion_Beneficiario_expectation)

        # Presenta Discapacidad
        Presenta_Discapacidad_expectation = gx.expectations.ExpectColumnValuesToBeInSet(
            column="Presenta Discapacidad",
            value_set=["SI", "NO"],
            mostly=0.98,
            severity="warning",
        )
        icbf_suite.add_expectation(Presenta_Discapacidad_expectation)

        # Estado UDS
        Estado_UDS_expectation = gx.expectations.ExpectColumnValuesToBeInSet(
            column="Estado UDS",
            value_set=["ACTIVA", "INACTIVA"],
            mostly=0.98,
            severity="warning",
        )
        icbf_suite.add_expectation(Estado_UDS_expectation)

        # ---------------------------------------------------------
        # Step 15 — Create and Register Validation Definition
        # ---------------------------------------------------------

        validation_definition = context.validation_definitions.add(
            gx.ValidationDefinition(
                name="icbf_validation_definition",
                data=batch_definition,
                suite=icbf_suite,
            )
        )

        print("Validation Definition created successfully.")

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
            print("Severity:", getattr(expectation, "severity", "N/A"))
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


if __name__ == "__main__":
        validations_icbf()