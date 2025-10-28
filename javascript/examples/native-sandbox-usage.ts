/**
 * Example: Using Native TypeScript Sandbox SDK
 * 
 * This example shows how to use the TypeScript SDK with native bindings
 * (same implementation as Python SDK via C FFI)
 */

import { PlatoSandboxClient, SimConfigDataset } from '../src/plato/native-bindings';

async function main() {
  // Initialize client
  const client = new PlatoSandboxClient(
    process.env.PLATO_API_KEY || 'your-api-key',
    process.env.PLATO_API_URL || 'https://plato.so/api'
  );

  try {
    // Example 1: Create sandbox from artifact ID (simplest)
    console.log('\n📦 Example 1: Creating sandbox from artifact...');
    const sandbox1 = await client.createSandbox({
      artifactId: 'art_example123',
      wait: true,  // Wait until ready (default)
      timeout: 600, // 10 minutes
    });
    console.log(`✅ Sandbox ready: ${sandbox1.public_id}`);
    console.log(`   URL: ${sandbox1.url}`);
    console.log(`   Status: ${sandbox1.status}`);

    // Example 2: Create sandbox from full configuration
    console.log('\n📦 Example 2: Creating sandbox from config...');
    const config: SimConfigDataset = {
      compute: {
        cpus: 2,
        memory: 1024,
        disk: 20480,
        app_port: 8080,
        plato_messaging_port: 7000,
      },
      metadata: {
        name: 'My Custom Sandbox',
        description: 'Example sandbox',
      },
    };

    const sandbox2 = await client.createSandbox({
      config,
      dataset: 'base',
      alias: 'example-sandbox',
      wait: true,
    });
    console.log(`✅ Sandbox ready: ${sandbox2.public_id}`);

    // Example 3: Setup SSH access
    console.log('\n🔐 Example 3: Setting up SSH access...');
    const sshInfo = await client.setupSSH(sandbox2, {
      localPort: 2222,
      username: 'plato',
    });
    console.log(`✅ SSH configured:`);
    console.log(`   Command: ${sshInfo.ssh_command}`);
    console.log(`   Config: ${sshInfo.ssh_config_path}`);

    // Example 4: Start proxy tunnel
    console.log('\n🔌 Example 4: Starting proxy tunnel...');
    const tunnel = await client.startProxyTunnel(sandbox2.public_id, 8080, 0);
    console.log(`✅ Tunnel started:`);
    console.log(`   Tunnel ID: ${tunnel.tunnel_id}`);
    console.log(`   Local port: ${tunnel.local_port}`);
    console.log(`   Access at: http://localhost:${tunnel.local_port}`);

    // Example 5: Create snapshot
    console.log('\n📸 Example 5: Creating snapshot...');
    const snapshot = await client.createSnapshot(sandbox2.public_id, {
      service: 'web',
      dataset: 'base',
    });
    console.log(`✅ Snapshot created:`);
    console.log(`   Artifact ID: ${snapshot.artifact_id}`);
    console.log(`   S3 URI: ${snapshot.s3_uri}`);

    // Example 6: List simulators
    console.log('\n📋 Example 6: Listing simulators...');
    const simulators = await client.listSimulators();
    console.log(`✅ Found ${simulators.length} simulators:`);
    simulators.slice(0, 5).forEach(sim => {
      console.log(`   - ${sim.name}: ${sim.description || 'No description'}`);
    });

    // Example 7: Get simulator versions
    if (simulators.length > 0) {
      console.log('\n🔖 Example 7: Getting simulator versions...');
      const versions = await client.getSimulatorVersions(simulators[0].name);
      console.log(`✅ Found ${versions.length} versions for ${simulators[0].name}`);
      versions.slice(0, 3).forEach(v => {
        console.log(`   - Version ${v.version}: ${v.artifact_id}`);
      });
    }

    // Example 8: Gitea operations
    console.log('\n🦊 Example 8: Gitea operations...');
    try {
      const creds = await client.getGiteaCredentials();
      console.log(`✅ Gitea credentials:`);
      console.log(`   User: ${creds.username}`);
      console.log(`   Org: ${creds.org_name}`);

      const giteaSimulators = await client.listGiteaSimulators();
      console.log(`   Found ${giteaSimulators.length} Gitea simulators`);
    } catch (err) {
      console.log(`   ⚠️  Gitea not available: ${err}`);
    }

    // Cleanup
    console.log('\n🧹 Cleaning up...');
    
    // Stop tunnel
    await client.stopProxyTunnel(tunnel.tunnel_id);
    console.log('✅ Tunnel stopped');

    // Close sandboxes
    await client.closeSandbox(sandbox1.public_id);
    console.log(`✅ Sandbox ${sandbox1.public_id} closed`);
    
    await client.closeSandbox(sandbox2.public_id);
    console.log(`✅ Sandbox ${sandbox2.public_id} closed`);

  } catch (error) {
    console.error('\n❌ Error:', error);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main().then(() => {
    console.log('\n✨ Example completed successfully!');
    process.exit(0);
  }).catch((error) => {
    console.error('\n❌ Example failed:', error);
    process.exit(1);
  });
}

export { main };

