class FixtureBank extends GSController {
  function Save() { return {}; }
  function Load(version, data) {}
  function Start() {
    GSLog.Info("FXBANK started=1");
    while (true) {
      if (GSCompany.ResolveCompanyID(0) == GSCompany.COMPANY_INVALID) { this.Sleep(1); continue; }
      // Sign visibility is company-scoped even for a GS (OpenTTD 15.3).
      local company = GSCompanyMode(0);
      local signs = GSSignList();
      for (local s = signs.Begin(); !signs.IsEnd(); s = signs.Next()) {
        local name = GSSign.GetName(s);
        if (name == null || name.len() < 5 || name.slice(0, 4) != "FXC:") continue;
        local target = name.slice(4).tointeger();
        company = null; // ChangeBankBalance requires deity mode.
        local before = GSCompany.GetBankBalance(0);
        local ok = GSCompany.ChangeBankBalance(0, target - before, GSCompany.EXPENSES_OTHER, GSMap.TILE_INVALID);
        GSLog.Info("FXBANK target=" + target + " before=" + before + " ok=" + (ok ? 1 : 0)
          + " after=" + GSCompany.GetBankBalance(0));
        if (!ok) throw "FIXTURE_BANK_COMMAND_FAILED";
        company = GSCompanyMode(0);
        if (!GSSign.SetName(s, "FXA:" + target)) throw "FIXTURE_ACK_FAILED";
      }
      company = null;
      this.Sleep(1);
    }
  }
}