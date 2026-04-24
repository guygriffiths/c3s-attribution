<script setup lang="ts">
import {
	IconChevronLeftPipe,
	IconChevronLeft,
	IconChevronRight,
	IconChevronRightPipe,
	IconPlayerPlay,
	IconChartBar,
	IconCalendarWeek,
} from '@tabler/icons-vue'

import { useStore } from '@/store/store'

const store = useStore()
</script>

<template>
	<div class="help-content">
		<p>The time reel provides fast and intuitive navigation through the entire 45+ years of extreme event data. To use the time reel in its current mode:
			<ul v-if="store.viewMode === 'timemachine'">
				<li>Scroll through the timeline to navigate different years</li>
				<li>Click and drag left or right to scrub through the days of the year</li>
				<li>View event bars representing extreme events that occurred on each day
				<ul>
					<li><strong>Length</strong> indicates the <strong>duration</strong> of the event</li>
					<li><strong>Colour</strong> indicates the <strong>temperature</strong> of the event</li>
					<li>Turn them off with the <span class="button glassy color decoration">
						<IconChartBar class="bar-icon" aria-hidden="true" />
					</span>
					<span class="sr-only">toggle event bars</span>
					button if they are distracting</li>
				</ul>
				</li>
						<li>Direct event selection
					<ul>
						<li>Click on any event bar in the time reel to select it</li>
						<li>The map will jump to the event's start date and highlight it</li>
						<li>Detailed event information will appear in the rankings panel</li>
					</ul>
				</li>
				<li>Navigation controls
					<ul>
						<li>
							Use the 
							<span class="button glassy color decoration">
								<IconChevronLeftPipe aria-hidden="true" />
							</span>
							<span class="sr-only">skip to start</span>
							and
							<span class="button glassy color decoration">
								<IconChevronRightPipe aria-hidden="true" />
							</span>
							<span class="sr-only">skip to end</span>
							buttons to jump to the start or end of the timeline
						</li>
						<li>
							Step forward or backward with the
							<span class="button glassy color decoration">
								<IconChevronLeft aria-hidden="true" />
							</span>
							<span class="sr-only">previous period</span>
							and
							<span class="button glassy color decoration">
								<IconChevronRight aria-hidden="true" />
							</span>
							<span class="sr-only">next period</span>
							buttons
						</li>
						<li>
							Use the
							<span class="button glassy color decoration">
								<IconPlayerPlay aria-hidden="true" />
							</span>
							<span class="sr-only">play/pause animation</span>
							button to animate the passage of time automatically
						</li>
					</ul>
				</li>

				<li>Use the <span class="button glassy color decoration">
					<IconCalendarWeek aria-hidden="true" />
				</span>
					<span class="sr-only">event history mode</span>
				button to switch to the full timeline view, which shows the full dataset at once.
				</li>
			</ul>
			<ul v-else>
				<li>The time reel spans the entire available period. Drag the shaded <strong>start</strong> and <strong>end</strong> handles to select the date range to display on the map, or drag the entire range.</li>
				<li>Using the play controls, you can move and animate the selected range around in time, showing long-term trends.</li>
				<li>Use this mode to see a global picture of events over a particular time period.</li>
			</ul>
		</p>
	</div>
</template>

<style lang="scss" scoped>
.help-content {
	max-height: 50vh;
}
</style>
