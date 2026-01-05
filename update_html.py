for i in range(6, 20):
    html = f'''
            <!-- Booth {i} -->
            <div class="col-md-4">
                <div class="card booth-card" id="booth-card-{i}">
                    <div class="card-header bg-primary text-white position-relative">
                        <h5 class="mb-0">🛂 Toll Booth {i}</h5>
                        <span class="closed-indicator" id="closed-indicator-booth_{i}">CLOSED</span>
                        <span class="breakdown-indicator" id="breakdown-indicator-booth_{i}">BREAKDOWN</span>
                    </div>
                    <div class="card-body">
                        <div class="booth-revenue">
                            <div>Revenue: <strong>$<span id="revenue-booth_{i}">0</span></strong></div>
                            <div>Vehicles: <span id="vehicles-booth_{i}">0</span></div>
                        </div>
                        <div id="queue-indicator-booth_{i}" class="queue-indicator queue-low">
                            Queue: <span id="queue-booth_{i}">0</span> vehicles
                        </div>
                        <div class="queue-bar">
                            <div id="queue-bar-booth_{i}" class="queue-fill" style="width: 0%"></div>
                        </div>
                        <div class="mt-2 text-muted small">
                            Occupancy: <span id="occupancy-booth_{i}">0</span>%
                        </div>
                        <label>Flow Rate (veh/hr):</label>
                        <div class="flow-control">
                            <input type="range" class="form-range" id="flow-booth_{i}" min="100" max="2000" value="100" step="50">
                            <input type="number" class="form-control" style="width: 100px" id="flow-value-booth_{i}" value="100" min="100" max="2000">
                        </div>
                        <button class="btn btn-sm btn-primary mt-2" onclick="updateFlow('booth_{i}')">Apply</button>
                        
                        <div class="breakdown-controls">
                            <label>Breakdown Control:</label>
                            <div class="btn-group w-100" role="group">
                                <button class="btn btn-sm btn-danger" onclick="triggerBreakdown('booth_{i}')">
                                    🚨 Trigger Breakdown
                                </button>
                                <button class="btn btn-sm btn-success" onclick="clearBreakdown('booth_{i}')">
                                    ✅ Clear Breakdown
                                </button>
                            </div>
                        </div>

                        <div class="lane-closure-controls">
                            <label>Lane Closure Control:</label>
                            <div class="btn-group w-100" role="group">
                                <button class="btn btn-sm btn-dark" onclick="closeLane('booth_{i}')">
                                    🚧 Close Lane
                                </button>
                                <button class="btn btn-sm btn-primary" onclick="openLane('booth_{i}')">
                                    ✅ Open Lane
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
'''
    print(html)