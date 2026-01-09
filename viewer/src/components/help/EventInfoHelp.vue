<script setup lang="ts">
import {
	IconStopwatch,
	IconDimensions,
	IconTemperature,
	IconSortDescendingSmallBig,
	IconSortAscendingSmallBig,
} from '@tabler/icons-vue'
import { useStore } from '@/store/store'

const store = useStore()
</script>

<template>
	<div class="help-content">
		<p>This panel provides detailed information about all of the events currently
		drawn on the map. From top-to-bottom, it features:
		<ul>
			<li>The number of events currently displayed.</li>
			<li>The selected date or date range currently being displayed.</li>
			<li>
				A rankings table of the (top 100) events being displayed.
				<ul>
					<li>
						Sorted by duration by default, but this can be changed with the
						<span class="button glassy decoration">
							<IconStopwatch
								v-if="store.focusVariable === 'duration'"
								aria-hidden="true"
							/>
							<IconDimensions
								v-else-if="store.focusVariable === 'size'"
								aria-hidden="true"
							/>
							<IconTemperature v-else aria-hidden="true" />
						</span>
						<span class="sr-only">
							toggle sort variable
						</span>
						button
					</li>
					<li>
						You can toggle between ascending and descending order with the
						<span class="button glassy decoration">
							<IconSortDescendingSmallBig
								v-if="store.sortDesc"
								aria-hidden="true"
							/>
							<IconSortAscendingSmallBig v-else aria-hidden="true" />
						</span>
						<span class="sr-only">
							toggle ascending/descending
						</span>
						button
					</li>
					<li>Each event is represented by a bar, where:
						<ul>
							<li><strong>Length</strong> indicates the <strong>duration</strong> of the event</li>
							<li><strong>Thickness</strong> indicates the <strong>area</strong> of the event</li>
							<li><strong>Colour</strong> indicates the <strong>temperature</strong> of the event</li>
						</ul>
					</li>
				</ul>
			</li>
			<li>Clicking on an event in the rankings table selects it to show further details.</li>
		</ul>
		</p>
	</div>
</template>

<style lang="scss" scoped>
</style>
