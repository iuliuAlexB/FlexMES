"""
Factory Pattern — STUB -directii viitoare .
Acuma OperationService.generate_for_wo() face operațiile direct, fără vreun layer intermediar.
"""
from models import Operation, WorkOrder


class OperationFactory:


    @staticmethod
    def create_for_work_order(wo: WorkOrder, routings: list) -> list[Operation]:
        #directii viitoare
        raise NotImplementedError("OperationFactory not yet implemented — use OperationService directly")
