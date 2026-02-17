@{
  ProjectRoot = "D:\病种分析V2"
  DatabaseUrl = "mysql+mysqlconnector://root:123456@127.0.0.1:3306/disease_analytics?charset=utf8mb4&use_pure=true"

  BackendPort = 18080
  FrontendPort = 5173

  # Optional: leave empty to auto-detect (py -> python -> python3)
  PythonCommand = ""
  PythonVersion = "3.12"
  WheelhouseDir = ""
  PrebuiltFrontendDist = ""

  InitDatabase = $true
  SeedData = $false
  SeedDataDir = ""

  InstallServices = $true
  OpenFirewall = $true
}
