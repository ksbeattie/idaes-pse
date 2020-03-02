##############################################################################
# Institute for the Design of Advanced Energy Systems Process Systems
# Engineering Framework (IDAES PSE Framework) Copyright (c) 2018-2019, by the
# software owners: The Regents of the University of California, through
# Lawrence Berkeley National Laboratory,  National Technology & Engineering
# Solutions of Sandia, LLC, Carnegie Mellon University, West Virginia
# University Research Corporation, et al. All rights reserved.
#
# Please see the files COPYRIGHT.txt and LICENSE.txt for full copyright and
# license information, respectively. Both files are also available online
# at the URL "https://github.com/IDAES/idaes-pse".
##############################################################################
"""
Tests for IDAES Stoichiometric reactor.

Author: Chinedu Okoli, Andrew Lee
"""
import pytest

from pyomo.environ import (ConcreteModel,
                           TerminationCondition,
                           SolverStatus,
                           value)
from idaes.core import (FlowsheetBlock,
                        MaterialBalanceType,
                        EnergyBalanceType,
                        MomentumBalanceType)

from idaes.core_lib.unit_models.stoichiometric_reactor import StoichiometricReactor

from idaes.core_lib.properties.examples.saponification_thermo import (
    SaponificationParameterBlock)
from idaes.core_lib.properties.examples.saponification_reactions import (
    SaponificationReactionParameterBlock)

from idaes.core.util.model_statistics import (degrees_of_freedom,
                                              number_variables,
                                              number_total_constraints,
                                              fixed_variables_set,
                                              activated_constraints_set,
                                              number_unused_variables)
from idaes.core.util.testing import (get_default_solver,
                                     PhysicalParameterTestBlock,
                                     ReactionParameterTestBlock)


# -----------------------------------------------------------------------------
# Get default solver for testing
solver = get_default_solver()


# -----------------------------------------------------------------------------
def test_config():
    m = ConcreteModel()
    m.fs = FlowsheetBlock(default={"dynamic": False})

    m.fs.properties = PhysicalParameterTestBlock()
    m.fs.reactions = ReactionParameterTestBlock(default={
                            "property_package": m.fs.properties})

    m.fs.unit = StoichiometricReactor(default={
            "property_package": m.fs.properties,
            "reaction_package": m.fs.reactions})

    # Check unit config arguments
    assert len(m.fs.unit.config) == 12

    assert m.fs.unit.config.material_balance_type == \
        MaterialBalanceType.useDefault
    assert m.fs.unit.config.energy_balance_type == \
        EnergyBalanceType.useDefault
    assert m.fs.unit.config.momentum_balance_type == \
        MomentumBalanceType.pressureTotal
    assert not m.fs.unit.config.has_heat_transfer
    assert not m.fs.unit.config.has_pressure_change
    assert not m.fs.unit.config.has_heat_of_reaction
    assert m.fs.unit.config.property_package is m.fs.properties
    assert m.fs.unit.config.reaction_package is m.fs.reactions


# -----------------------------------------------------------------------------
class TestSaponification(object):
    @pytest.fixture(scope="class")
    def sapon(self):
        m = ConcreteModel()
        m.fs = FlowsheetBlock(default={"dynamic": False})

        m.fs.properties = SaponificationParameterBlock()
        m.fs.reactions = SaponificationReactionParameterBlock(default={
                                "property_package": m.fs.properties})

        m.fs.unit = StoichiometricReactor(default={
                "property_package": m.fs.properties,
                "reaction_package": m.fs.reactions,
                "has_heat_transfer": True,
                "has_heat_of_reaction": True,
                "has_pressure_change": True})

        return m

    @pytest.mark.build
    def test_build(self, sapon):

        assert hasattr(sapon.fs.unit, "inlet")
        assert len(sapon.fs.unit.inlet.vars) == 4
        assert hasattr(sapon.fs.unit.inlet, "flow_vol")
        assert hasattr(sapon.fs.unit.inlet, "conc_mol_comp")
        assert hasattr(sapon.fs.unit.inlet, "temperature")
        assert hasattr(sapon.fs.unit.inlet, "pressure")

        assert hasattr(sapon.fs.unit, "outlet")
        assert len(sapon.fs.unit.outlet.vars) == 4
        assert hasattr(sapon.fs.unit.outlet, "flow_vol")
        assert hasattr(sapon.fs.unit.outlet, "conc_mol_comp")
        assert hasattr(sapon.fs.unit.outlet, "temperature")
        assert hasattr(sapon.fs.unit.outlet, "pressure")

        assert hasattr(sapon.fs.unit, "rate_reaction_extent")

        assert number_variables(sapon) == 24
        assert number_total_constraints(sapon) == 13
        assert number_unused_variables(sapon) == 0

    def test_dof(self, sapon):
        sapon.fs.unit.inlet.flow_vol.fix(1)
        sapon.fs.unit.inlet.conc_mol_comp[0, "H2O"].fix(55388.0)
        sapon.fs.unit.inlet.conc_mol_comp[0, "NaOH"].fix(100.0)
        sapon.fs.unit.inlet.conc_mol_comp[0, "EthylAcetate"].fix(100.0)
        sapon.fs.unit.inlet.conc_mol_comp[0, "SodiumAcetate"].fix(0.0)
        sapon.fs.unit.inlet.conc_mol_comp[0, "Ethanol"].fix(0.0)

        sapon.fs.unit.inlet.temperature.fix(303.15)
        sapon.fs.unit.inlet.pressure.fix(101325.0)

        sapon.fs.unit.rate_reaction_extent[0, 'R1'].fix(90)
        sapon.fs.unit.heat_duty.fix(0)
        sapon.fs.unit.deltaP.fix(0)

        assert degrees_of_freedom(sapon) == 0

    @pytest.mark.initialize
    @pytest.mark.solver
    @pytest.mark.skipif(solver is None, reason="Solver not available")
    def test_initialize(self, sapon):
        orig_fixed_vars = fixed_variables_set(sapon)
        orig_act_consts = activated_constraints_set(sapon)

        sapon.fs.unit.initialize(optarg={'tol': 1e-6})

        assert degrees_of_freedom(sapon) == 0

        fin_fixed_vars = fixed_variables_set(sapon)
        fin_act_consts = activated_constraints_set(sapon)

        assert len(fin_act_consts) == len(orig_act_consts)
        assert len(fin_fixed_vars) == len(orig_fixed_vars)

        for c in fin_act_consts:
            assert c in orig_act_consts
        for v in fin_fixed_vars:
            assert v in orig_fixed_vars

    @pytest.mark.solver
    @pytest.mark.skipif(solver is None, reason="Solver not available")
    def test_solve(self, sapon):
        results = solver.solve(sapon)

        # Check for optimal solution
        assert results.solver.termination_condition == \
            TerminationCondition.optimal
        assert results.solver.status == SolverStatus.ok

    @pytest.mark.initialize
    @pytest.mark.solver
    @pytest.mark.skipif(solver is None, reason="Solver not available")
    def test_solution(self, sapon):
        assert (pytest.approx(101325.0, abs=1e-2) ==
                value(sapon.fs.unit.outlet.pressure[0]))
        assert (pytest.approx(304.21, abs=1e-2) ==
                value(sapon.fs.unit.outlet.temperature[0]))
        assert (pytest.approx(90, abs=1e-2) ==
                value(sapon.fs.unit.outlet.conc_mol_comp[0, "Ethanol"]))

    @pytest.mark.initialize
    @pytest.mark.solver
    @pytest.mark.skipif(solver is None, reason="Solver not available")
    def test_conservation(self, sapon):
        assert abs(value(sapon.fs.unit.inlet.flow_vol[0] -
                         sapon.fs.unit.outlet.flow_vol[0])) <= 1e-6
        assert (abs(value(sapon.fs.unit.inlet.flow_vol[0] *
                          sum(sapon.fs.unit.inlet.conc_mol_comp[0, j]
                              for j in sapon.fs.properties.component_list) -
                          sapon.fs.unit.outlet.flow_vol[0] *
                          sum(sapon.fs.unit.outlet.conc_mol_comp[0, j]
                              for j in sapon.fs.properties.component_list)))
                <= 1e-6)

        assert (pytest.approx(4410000, abs=1e3) == value(
                sapon.fs.unit.control_volume.heat_of_reaction[0]))
        assert abs(value(
                (sapon.fs.unit.inlet.flow_vol[0] *
                 sapon.fs.properties.dens_mol *
                 sapon.fs.properties.cp_mol *
                 (sapon.fs.unit.inlet.temperature[0] -
                    sapon.fs.properties.temperature_ref)) -
                (sapon.fs.unit.outlet.flow_vol[0] *
                 sapon.fs.properties.dens_mol *
                 sapon.fs.properties.cp_mol *
                 (sapon.fs.unit.outlet.temperature[0] -
                  sapon.fs.properties.temperature_ref)) +
                sapon.fs.unit.control_volume.heat_of_reaction[0])) <= 1e-3

    @pytest.mark.ui
    def test_report(self, sapon):
        sapon.fs.unit.report()