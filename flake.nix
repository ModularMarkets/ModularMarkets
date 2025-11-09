{
  description = "Market Maker App - Python project with Nix flake dev shell";

  # MODULAR PLATFORM SUPPORT
  # This flake supports selective inclusion of platform-specific dependencies.
  #
  # Usage examples:
  #   - Default (all platforms):     nix develop
  #   - Minecraft only:              nix develop .#minecraft-only
  #   - Core only (no platforms):    nix develop .#core-only
  #
  # To add a new platform:
  #   1. Add the platform name to the platforms list below
  #   2. Ensure src/platforms/<platform>/requirements.txt exists
  #   3. Dependencies are automatically installed from requirements.txt files via pip
  #
  # The flake uses a virtual environment approach - packages are installed via pip
  # from requirements.txt files, so you never need to update the flake when adding
  # new packages to requirements.txt.
  #
  # Platform-specific notes:
  #   - Minecraft platform: Requires Node.js for the mineflayer service
  #     Node.js dependencies are automatically installed from package.json when
  #     the minecraft platform is enabled.

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    let
      # PLATFORM LIST - Add new platforms here
      # Platforms are automatically discovered from src/platforms/<name>/requirements.txt
      platforms = [
        "minecraft"
        # Add more platforms here as they are implemented
        # "example"
      ];
    in
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        
        # Helper function to create a devShell with specific platforms
        # Uses venv approach - pip installs from requirements.txt automatically
        mkDevShell = { platforms, name ? "default" }:
          pkgs.mkShell {
            name = "modular-markets-${name}";
            packages = [
              pkgs.python3
              pkgs.python3Packages.pip
              pkgs.pkg-config
              pkgs.openssl
              pkgs.zlib
              pkgs.sqlite
              pkgs.nodejs_22
              pkgs.nodePackages.npm
            ];
            
            shellHook = ''
              export PIP_DISABLE_PIP_VERSION_CHECK=1
              export VENV_DIR=".venv"
              
              # Create venv if it doesn't exist
              if [ ! -d "$VENV_DIR" ]; then
                python -m venv "$VENV_DIR"
              fi
              . "$VENV_DIR/bin/activate"
              
              # Function to install requirements.txt if it exists and has changed
              install_requirements() {
                local req_file="$1"
                local platform_name="$2"
                
                if [ -f "$req_file" ]; then
                  # Calculate hash of requirements file
                  REQ_HASH=$(sha256sum "$req_file" | cut -d" " -f1)
                  HASH_FILE="$VENV_DIR/.req-hash-$platform_name"
                  
                  # Install only if hash changed or file doesn't exist
                  if [ ! -f "$HASH_FILE" ] || [ "$(cat "$HASH_FILE" 2>/dev/null)" != "$REQ_HASH" ]; then
                    echo "Installing dependencies from $req_file..."
                    python -m pip install --upgrade pip wheel
                    pip install -r "$req_file"
                    echo "$REQ_HASH" > "$HASH_FILE"
                    echo "✓ Installed dependencies from $req_file"
                  fi
                fi
              }
              
              # Install core requirements
              install_requirements "requirements.txt" "core"
              
              # Install platform-specific requirements for selected platforms
              ${builtins.concatStringsSep "\n" (builtins.map (platform: ''
              install_requirements "src/platforms/${platform}/requirements.txt" "${platform}"
              '') platforms)}
              
              # Install Node.js dependencies for mineflayer service (if minecraft platform is enabled)
              ${if builtins.elem "minecraft" platforms then ''
              NODE_SERVICE_DIR="src/platforms/minecraft/node_service"
              if [ -f "$NODE_SERVICE_DIR/package.json" ]; then
                if [ ! -d "$NODE_SERVICE_DIR/node_modules" ]; then
                  echo "Installing Node.js dependencies for mineflayer service..."
                  cd "$NODE_SERVICE_DIR"
                  npm install
                  cd - > /dev/null
                  echo "✓ Installed Node.js dependencies"
                else
                  echo "✓ Node.js dependencies already installed"
                fi
              fi
              '' else ""}
              
              echo ""
              echo "Market Maker App development environment"
              echo "Python: $(python --version)"
              echo "Node.js: $(node --version)"
              echo "Enabled platforms: ${if platforms == [] then "none" else builtins.concatStringsSep ", " platforms}"
              echo "Venv active: $VENV_DIR"
              echo ""
              echo "Run tests with: pytest tests/"
              echo "Run API server with: python main.py"
              ${if builtins.elem "minecraft" platforms then ''
              echo "Start mineflayer service with: cd src/platforms/minecraft/node_service && npm start"
              '' else ""}
            '';
          };
        
        # Default: include all available platforms
        defaultPlatforms = platforms;
        
      in
      {
        # Default devShell includes all platforms
        devShells.default = mkDevShell { platforms = defaultPlatforms; };
        
        # Platform-specific devShells for selective inclusion
        # Usage: nix develop .#minecraft-only
        devShells.minecraft-only = mkDevShell { 
          platforms = [ "minecraft" ]; 
          name = "minecraft-only";
        };
        
        # Core-only devShell (no platform-specific dependencies)
        # Usage: nix develop .#core-only
        devShells.core-only = mkDevShell { 
          platforms = []; 
          name = "core-only";
        };
      }
    );
}

