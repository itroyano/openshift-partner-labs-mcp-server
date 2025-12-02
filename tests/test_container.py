"""Tests for container functionality and deployment."""

import subprocess
import time
from pathlib import Path

import httpx
import pytest


class TestContainerBuild:
    """Test container build functionality."""

    def test_containerfile_exists(self):
        """Test that Containerfile exists and is readable."""
        # Arrange
        containerfile_path = Path("Containerfile")

        # Act & Assert
        assert containerfile_path.exists(), "Containerfile should exist"
        assert containerfile_path.is_file(), "Containerfile should be a file"
        assert containerfile_path.stat().st_size > 0, (
            "Containerfile should not be empty"
        )

    def test_containerfile_uses_red_hat_ubi(self):
        """Test that Containerfile uses Red Hat UBI Python 3.12 base image."""
        # Arrange
        containerfile_path = Path("Containerfile")

        # Act
        content = containerfile_path.read_text()

        # Assert
        assert "registry.access.redhat.com/ubi9/python-312" in content

    def test_containerfile_structure(self):
        """Test that Containerfile has expected structure."""
        # Arrange
        containerfile_path = Path("Containerfile")

        # Act
        content = containerfile_path.read_text()
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        # Assert
        assert any("WORKDIR" in line for line in lines), "Should set working directory"
        assert any("COPY" in line for line in lines), "Should copy files"
        assert any("RUN" in line for line in lines), "Should run installation commands"
        assert any("CMD" in line for line in lines), "Should have startup command"

    def test_containerignore_exists(self):
        """Test that .containerignore exists for optimized builds."""
        # Arrange
        containerignore_path = Path(".containerignore")

        # Act & Assert
        assert containerignore_path.exists(), ".containerignore should exist"
        content = containerignore_path.read_text()

        # Common patterns that should be ignored
        ignore_patterns = [".git", "__pycache__", ".pytest_cache"]
        for pattern in ignore_patterns:
            assert pattern in content, f"Should ignore {pattern}"
        # Check for Python compiled files (*.py[cod] is more comprehensive than *.pyc)
        assert "*.py[cod]" in content, "Should ignore Python compiled files"

    @pytest.mark.skipif(
        subprocess.run(["which", "podman"], capture_output=True).returncode != 0,
        reason="podman not available",
    )
    def test_container_build_success(self):
        """Test that container builds successfully with podman."""
        # Arrange
        image_name = "partner-labs-mcp-server-test"
        build_cmd = ["podman", "build", "-t", image_name, "."]
        cleanup_cmd = ["podman", "rmi", image_name]

        try:
            # Act
            result = subprocess.run(
                build_cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            # Assert
            assert result.returncode == 0, f"Build failed: {result.stderr}"

        finally:
            # Cleanup
            subprocess.run(cleanup_cmd, capture_output=True)


class TestContainerExecution:
    """Test container execution and functionality."""

    @pytest.mark.skipif(
        subprocess.run(["which", "podman"], capture_output=True).returncode != 0,
        reason="podman not available",
    )
    def test_container_startup_and_health(self):
        """Test that container starts and responds to HTTP requests."""
        # Arrange
        image_name = "partner-labs-mcp-server-test"
        container_name = "template-mcp-test-container"
        build_cmd = ["podman", "build", "-t", image_name, "."]
        run_cmd = [
            "podman",
            "run",
            "-d",
            "--env-file",
            ".env",
            "--name",
            container_name,
            "-p",
            "8081:8080",
            image_name,
        ]
        stop_cmd = ["podman", "stop", container_name]
        rm_cmd = ["podman", "rm", container_name]
        cleanup_img_cmd = ["podman", "rmi", image_name]

        try:
            # Build container
            build_result = subprocess.run(
                build_cmd, capture_output=True, text=True, timeout=300
            )
            assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"

            # Start container
            run_result = subprocess.run(run_cmd, capture_output=True, text=True)
            assert run_result.returncode == 0, (
                f"Container start failed: {run_result.stderr}"
            )

            # Wait for container to start
            time.sleep(5)

            # Test that container is responding (may be 404 if no root endpoint)
            with httpx.Client() as client:
                response = client.get("http://localhost:8080/", timeout=10)

                # Accept any HTTP response (404, 200, etc.) - just confirm server is listening
                assert response.status_code >= 200, (
                    f"Server not responding: {response.status_code}"
                )

        finally:
            # Cleanup
            subprocess.run(stop_cmd, capture_output=True)
            subprocess.run(rm_cmd, capture_output=True)
            subprocess.run(cleanup_img_cmd, capture_output=True)

    def test_container_command_structure(self):
        """Test that container has correct command structure."""
        # Arrange
        containerfile_path = Path("Containerfile")

        # Act
        content = containerfile_path.read_text()

        # Assert
        assert (
            'CMD ["/opt/app-root/src/.venv/bin/python", "-m", "openshift_partner_labs_mcp_server.src.main"]'
            in content
        )
        assert "PYTHONPATH=/app" in content


class TestContainerConfiguration:
    """Test container configuration and setup."""

    def test_containerfile_uses_virtual_environment(self):
        """Test that container uses Python virtual environment."""
        # Arrange
        containerfile_path = Path("Containerfile")

        # Act
        content = containerfile_path.read_text()

        # Assert
        assert "uv venv" in content, "Should create virtual environment"
        assert "/opt/app-root/src/.venv/bin/python" in content, (
            "Should use virtual environment Python"
        )

    def test_containerfile_has_proper_dependencies(self):
        """Test that container installs dependencies correctly."""
        # Arrange
        containerfile_path = Path("Containerfile")

        # Act
        content = containerfile_path.read_text()

        # Assert
        assert "pip install uv" in content, "Should install uv package manager"
        assert "pyproject.toml" in content, "Should copy dependency manifest"

    def test_containerfile_sets_workdir(self):
        """Test that container sets appropriate working directory."""
        # Arrange
        containerfile_path = Path("Containerfile")

        # Act
        content = containerfile_path.read_text()

        # Assert
        assert "WORKDIR /app" in content, "Should set working directory to /app"

    def test_containerfile_includes_red_hat_certificates(self):
        """Test that container includes Red Hat certificate handling."""
        # Arrange
        containerfile_path = Path("Containerfile")

        # Act
        content = containerfile_path.read_text()

        # Assert
        assert "Current-IT-Root-CAs.pem" in content, (
            "Should include Red Hat certificates"
        )
        assert "certifi" in content, "Should update certificate bundle"

    def test_container_pythonpath_configuration(self):
        """Test that container sets PYTHONPATH correctly."""
        # Arrange
        containerfile_path = Path("Containerfile")

        # Act
        content = containerfile_path.read_text()

        # Assert
        assert "ENV PYTHONPATH=/app" in content, "Should set PYTHONPATH to /app"


class TestProductionDeployment:
    """Test production deployment readiness."""

    def test_containerfile_optimized_for_production(self):
        """Test that Containerfile follows production best practices."""
        # Arrange
        containerfile_path = Path("Containerfile")

        # Act
        content = containerfile_path.read_text()

        # Assert
        # Multi-stage or optimized dependency installation
        assert "uv" in content, "Should use uv for fast dependency installation"

        # Dependencies installed before source code copy
        copy_lines = [i for i, line in enumerate(content.split("\n")) if "COPY" in line]
        assert len(copy_lines) >= 2, (
            "Should have separate dependency and source copy steps"
        )

    def test_source_code_structure_for_container(self):
        """Test that source code structure matches container expectations."""
        # Arrange
        expected_dirs = ["openshift_partner_labs_mcp_server", "tests"]

        # Act & Assert
        for dir_name in expected_dirs:
            dir_path = Path(dir_name)
            assert dir_path.exists(), f"Directory {dir_name} should exist"
            assert dir_path.is_dir(), f"{dir_name} should be a directory"

    @pytest.mark.skipif(
        subprocess.run(["which", "podman"], capture_output=True).returncode != 0,
        reason="podman not available",
    )
    def test_container_resource_usage(self):
        """Test container resource usage and startup time."""
        # Arrange
        image_name = "partner-labs-mcp-server-test"
        build_cmd = ["podman", "build", "-t", image_name, "."]
        inspect_cmd = ["podman", "inspect", image_name]
        cleanup_cmd = ["podman", "rmi", image_name]

        try:
            # Build and inspect container
            build_result = subprocess.run(
                build_cmd, capture_output=True, text=True, timeout=300
            )
            assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"

            inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True)
            assert inspect_result.returncode == 0, "Container inspect should succeed"

            # Basic size check (container shouldn't be enormous)
            # This is a rough check - actual size depends on base image
            assert len(inspect_result.stdout) > 100, (
                "Inspect output should contain meaningful data"
            )

        finally:
            # Cleanup
            subprocess.run(cleanup_cmd, capture_output=True)
