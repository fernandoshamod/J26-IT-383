import unittest
from component4.manual_model_check import read_value, collect_inputs, display, run, DEFAULTS

PROFILE={'guest_min':90,'guest_max':180,'event_hours':[4,5,6,7],
         'stage_width_m':[3,4,5],'stage_length_m':[2.25,3,4,6],
         'budget_score':[2,3,4],'retained_receipts_score':[2,3,4]}


class ManualModelCheckTests(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(collect_inputs(PROFILE,reader=lambda _: '',writer=lambda _:None),DEFAULTS)

    def test_guest_reprompt_and_integer(self):
        answers=iter(['nan','100.2','181','120'])
        output=[]
        self.assertEqual(read_value('guests',100,PROFILE,reader=lambda _:next(answers),writer=output.append),120)
        self.assertEqual(len(output),3)

    def test_rupees_rejected_and_supported_budget(self):
        answers=iter(['500000','inf','3'])
        output=[]
        self.assertEqual(read_value('budget_score',3,PROFILE,reader=lambda _:next(answers),writer=output.append),3)
        self.assertEqual(len(output),2)

    def test_unsupported_duration_reprompt(self):
        answers=iter(['4.5','5'])
        self.assertEqual(read_value('event_hours',4,PROFILE,reader=lambda _:next(answers),writer=lambda _:None),5)

    def test_blocked_display(self):
        lines=[]
        display({'status':'blocked','blockers':['geometry_invalid']},writer=lines.append)
        self.assertTrue(any('geometry_invalid' in line for line in lines))
        self.assertFalse(any('score=' in line for line in lines))

    def test_actual_saved_models_interactive_baseline_and_what_if(self):
        from component4.unitless_decision_support import UnitlessDecisionSupport
        service=UnitlessDecisionSupport()
        answers=iter(['1']+['']*6+['y','120','7','3','6','3','4','q'])
        lines=[]
        run(service,reader=lambda _:next(answers),writer=lines.append,save=False)
        self.assertTrue(any('total_cost_score: 2.7000' in line for line in lines))
        self.assertTrue(any('total_cost_score: 3.5386' in line for line in lines))
        self.assertTrue(any('Budget_Overrun: score=' in line for line in lines))
        self.assertTrue(any('Planned costs exceed budget.' in line for line in lines))
        self.assertFalse(any('Full results saved' in line for line in lines))
