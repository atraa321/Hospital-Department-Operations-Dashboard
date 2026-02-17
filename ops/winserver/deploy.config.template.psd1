@{
  # Target installation directory on the Windows Server.
  ProjectRoot = "D:\病种分析V2"

  # Optional: leave empty to auto-detect (py -> python -> python3), or set absolute path.
  PythonCommand = ""
  PythonVersion = "3.12"

  # Required: replace with real MySQL connection information.
  DatabaseUrl = "mysql+pymysql://root:你的密码@127.0.0.1:3306/disease_analytics?charset=utf8mb4"

  BackendPort = 18080
  FrontendPort = 5173

  # Use empty string to auto-calculate from BackendPort.
  ApiBaseUrl = ""

  # Optional explicit CORS JSON array (for example: ["http://10.10.10.20:5173"]).
  CorsOriginsJson = ""

  InstallServices = $true
  OpenFirewall = $true
  InitDatabase = $true

  # If true, import seed files from BundleRoot\seed_data.
  SeedData = $false
  SeedDataDirName = "seed_data"

  # If true, restore bundled snapshot SQL after deployment.
  RestoreSnapshot = $false

  # Relative paths are based on bundle root directory.
  SnapshotSqlRelativePath = "data_snapshot\database.sql"
  SnapshotUploadsRelativePath = "data_snapshot\uploads"
  RestoreUploads = $true

  # Backend upload folder relative to ProjectRoot.
  UploadDirRelativePath = "backend\data\uploads"

  # Optional: set MySQL bin directory containing mysql.exe.
  # Example: C:\Program Files\MySQL\MySQL Server 8.0\bin
  MySqlBinDir = ""
}
