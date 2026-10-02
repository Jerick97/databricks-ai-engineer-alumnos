"""Complemento CP3: custom model sobre ventas UC reales para plataformas sin split de agentes."""
import json,time
import pandas as pd
import mlflow
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementParameterListItem

class NeptunoVentas(mlflow.pyfunc.PythonModel):
    def load_context(self,context):
        self.config=context.model_config
        self.w=WorkspaceClient()
    def predict(self,context,model_input,params=None):
        rows=[]
        for item in model_input.to_dict('records'):
            year=int(item['anio']);category=str(item['categoria'])
            r=self.w.statement_execution.execute_statement(warehouse_id=self.config['warehouse_id'],
                statement=f"SELECT {self.config['function_name']}(:categoria,:anio) AS result",
                parameters=[StatementParameterListItem(name='categoria',value=category,type='STRING'),StatementParameterListItem(name='anio',value=str(year),type='INT')],wait_timeout='50s')
            deadline=time.monotonic()+120
            while r.status.state.value in {'PENDING','RUNNING'} and time.monotonic()<deadline:
                time.sleep(2);r=self.w.statement_execution.get_statement(r.statement_id)
            if r.status.state.value!='SUCCEEDED':raise RuntimeError('SQL no completó')
            data=json.loads(r.result.data_array[0][0]);data['revision']=self.config['revision'];rows.append(data)
        return pd.DataFrame(rows)
mlflow.models.set_model(NeptunoVentas())
