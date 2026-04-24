<script setup lang="ts">
import {
	IconSteeringWheel,
	IconChevronDown,
	IconUsers,
	IconWorldHeart,
	IconAlertTriangle,
	IconChartHistogram,
	IconCalendarTime,
	IconEyePin,
	IconInfoOctagon,
	IconHelp,
} from '@tabler/icons-vue'
import { useStore } from '@/store/store'
import { useLabels } from '@/lib/labels'

const $l = useLabels()

const store = useStore()
// h2>How to use this App:</h2>

// <h2>About ECMWF:</h2>

// <p></p>

// <h2>About ERA5:</h2>

// <h2>About this data:</h2>

// <h2>Access the code:</h2>

// <p>Not for this release – suggest not including this section
// for this release.</p>

// <h2>Disclaimer:</h2>

// </div>

const aboutInfoContent = [
	{
		title: 'About ECMWF',
		subtitle: 'Who we are and what we do',
		icon: 'IconUsers',
		content: ` <p>We are both a&nbsp;<b>research institute</b>&nbsp;and an&nbsp;<b>24/7 operational service</b>, producing global numerical weather predictions and other data for our&nbsp;<b>Member and Co-operating States</b>&nbsp;and the broader community. We operate a&nbsp;<b>world-class supercomputer facility</b>&nbsp;for weather forecasting and hold one of the&nbsp;<b>largest meteorological data archives</b>.</p> `,
	},
	{
		title: 'About ERA5',
		subtitle: 'Spatially complete reanalysis',
		icon: 'IconWorldHeart',
		content: `<p> All of the climate statistics generated and visualised by this application are derived from the&nbsp;<b>ERA5</b>&nbsp;reanalysis dataset, which is available to download and use under the CC-BY 4.0 licence&nbsp;<a href="https://cds.climate.copernicus.eu/datasets/derived-era5-single-levels-daily-statistics?tab=overview" target="_blank" >here</a >.&nbsp;<b>ERA5</b>&nbsp;is a global&nbsp;<b>atmospheric reanalysis</b >&nbsp;that covers the period from 1940 to present and is developed and maintained by&nbsp;<b>ECMWF</b>. It combines direct observations with a numerical model to create a global estimate of various climate variables. This application uses the post-processed&nbsp;<b>daily statistics, </b>on a regular 0.25° × 0.25° grid. </p> <p> The information presented by this application uses a clustering algorithm to group individual grid-cells associated with extreme events (e.g. heatwaves and cold spells) for specific locations. Individual pixels are from the post-processed&nbsp;<b>ERA5</b>&nbsp;reanalysis and is not based on site-specific observations. Individual grid cells on the interpolated grid are typically several hundred square kilometres in size and represent the average environment at that location. Extreme event summary statistics are calculated from all pixels associated with a particular event. </p> <p> There are several notable caveats to consider when interpreting the&nbsp;<b>ERA5</b>&nbsp;data presented here: Due to changes in the observational network through time, limited observations in the early decades decrease the reliability of&nbsp;<b>ERA5</b>&nbsp;during that period (<a href="https://doi.org/10.1002/qj.4803" target="_blank" >Soci et al., 2024</a >). Therefore, this application currently shows data from 1979 to present only. </p> <p> Users wishing to draw conclusions about long-term climate trends downloaded from the app should be aware of the caveats and limitations related to&nbsp;<b>ERA5</b>&nbsp;data and are invited to consult the documentation. The explorer is designed to make exploring&nbsp;<b>extreme events</b>&nbsp;a faster and easier task, but should not be seen as a full scientific analysis, which would require further investigations, such as comparing ERA5 data to other data sources. </p> <p> For further information, the user is encouraged to begin with the&nbsp;<a href="https://climate.copernicus.eu/reanalysis-qas" target="_blank" >Reanalysis FAQs</a >. </p> `,
	},
	{
		title: 'About the data shown',
		subtitle: 'How to interpret this data',
		icon: 'IconChartHistogram',
		content: `<p><b>Temperature data</b></p> <p>This application uses&nbsp;<b>2 metre temperature</b>&nbsp;from&nbsp;<b>ERA5</b>, which represents the air temperature at 2 metres above the surface. Over land, near-surface temperature observations from weather stations are combined with the model output to improve accuracy. The 2 metre temperature is influenced by environmental factors like land type and vegetation. Note that&nbsp;<b>ERA5</b>&nbsp;does not explicitly represent urban environments, meaning it may not fully capture the&nbsp;<i>urban heat island</i>&nbsp;effect commonly observed in cities. </p> <p>The daily aggregation statistics used are daily maximum temperature for heatwaves, and daily minimum temperature for cold spells. For more information see the <a href="https://confluence.ecmwf.int/display/CKB/ERA5+family+post-processed+daily+statistics+documentation" target="_blank">associated documentation</a>.</p> <p><b>Event definition:</b></p> <p>Events are detected using a clustering algorithm, which groups together spatiotemporally nearby grid cells which:</p> <p><b>For heat waves:</b></p> <ul><li>Exceed the 99th percentile value for that location (average daily maximum at that cell over the period 1991-2020).</li><li>Exceed an absolute threshold of 28°C</li><li>Do so for at least 3 consecutive days</li></ul> <p><b>For cold spells:</b></p> <ul><li>Fall below the 1st percentile value for that location (average daily maximum at that cell over the period 1991-2020).</li><li>Fall below an absolute threshold of 0°C</li><li>Do so for at least 3 consecutive days</li></ul> <p>See <a href="${import.meta.env.X_PUBLIC_PATH}Clustering%20Algorithm%20Description.pdf" target="_blank">the clustering algorithm description</a> for further details.</p>`,
	},
	{
		title: 'Disclaimer',
		icon: 'IconAlertTriangle',
		content: `<p>The designations employed and the presentation of material on this app do not imply the expression of any opinion whatsoever on the part of the European Union concerning the legal status of any country, territory or area or of its authorities, or concerning the delimitation of its frontiers or boundaries. </p>`,
	},
]
const iconMap = {
	IconSteeringWheel,
	IconUsers,
	IconWorldHeart,
	IconAlertTriangle,
	IconChartHistogram,
}

const getIconComponent = (iconName: string) => {
	return iconMap[iconName as keyof typeof iconMap] || null
}
</script>

<template>
	<div class="help-content">
		<div class="drawer">
			<div class="drawer-front">
				<div class="label">
					<IconSteeringWheel class="icon" aria-hidden="true" />
					<div class="label-text">
						<h1>Welcome to Extremes ERA!</h1>
						<h2>Discover extreme weather events from around the globe</h2>
					</div>
				</div>
			</div>
			<div class="drawer-contents open">
				<p>
					Discover extreme weather events from around the globe, from
					present-day events to historical events dating back to 1979. As
					climate change is altering the frequency and intensity of extreme
					weather events such as heat waves, cold spells and extreme
					precipitation, this app allows you to explore individual extreme
					events, identify hotspots and uncover trends over time.
				</p>
				<p>
					Filter events by a specific temperature or precipitation threshold, a
					minimum duration or affected area!
				</p>
				<p>There are two modes of the application:</p>
				<div class="mainmodes">
					<div class="timemachine">
						<div class="button glassy color decoration">
							<IconCalendarTime size="32" aria-hidden="true" />
						</div>
						<h2>Time Machine</h2>
						<p>
							You can explore extreme temperature events from 1979 to present
							day. Select a year and day and events will appear as polygons on a
							map. Click on an event to view more detailed statistics.
						</p>
					</div>
					<div class="heatmap">
						<div class="button glassy color decoration">
							<IconEyePin size="32" aria-hidden="true" />
						</div>
						<h2>Overview</h2>
						<p>
							You can visualize the frequency and intensity of extreme
							temperature events. Select a year or range of years, and all
							events during that period will be displayed, allowing you to
							identify hotspots and trends in extreme temperatures and
							precipitation.
						</p>
					</div>
				</div>
				<p>
					Check <div class="button glassy color decoration"><IconInfoOctagon size="20" v-tooltip="$l.aboutInfo" /></div> at any time for
					more detailed information. The <div class="button glassy color decoration"><IconHelp size="20"v-tooltip="$l.help" /></div> icon
					will provide guidance for how to use or interpret specific features.
				</p>
				<p>
					You can switch between different types of extremes (heatwaves, cold
					spells, all events) at any time using the event type selector.
				</p>
			</div>
		</div>
		<div
			class="drawer"
			v-for="content in aboutInfoContent"
			:key="content.title"
		>
			<div class="drawer-front">
				<div class="label">
					<component
						:is="getIconComponent(content.icon)"
						class="icon"
						aria-hidden="true"
					/>
					<div class="label-text">
						<h1>{{ content.title }}</h1>
						<h2 v-if="content.subtitle">{{ content.subtitle }}</h2>
					</div>
				</div>
				<button
					class="expand-small glassy flat"
					:aria-label="
						store.aboutSectionOpen === content.title
							? 'Collapse section'
							: 'Expand section'
					"
					@click="
						store.aboutSectionOpen =
							content.title === store.aboutSectionOpen ? null : content.title
					"
				>
					<IconChevronDown
						class="icon"
						:class="{ open: store.aboutSectionOpen === content.title }"
						aria-hidden="true"
					/>
				</button>
			</div>
			<div
				class="drawer-contents"
				:class="{ open: store.aboutSectionOpen === content.title }"
				v-html="content.content"
			></div>
		</div>
	</div>
	<div></div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

.help-content {
	display: flex;
	flex-direction: column;
	gap: 0;
	height: 100vh;
	padding: 0;

	p {
		font-size: 1.1rem;
	}

	.drawer {
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: $panelMargin;
		background: var(--panel-bg);
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: space-between;

		.drawer-front {
			display: flex;
			align-items: center;
			width: 100%;
			gap: 1rem;
		}

		.drawer-contents {
			max-height: 0;
			overflow: hidden;
			width: 100%;
			transition: all $transition;
			li {
				font-size: 1.1rem;
			}
			&.open {
				max-height: 2000px; /* Large enough to fit content */
				margin-top: 1rem;
			}

			.mainmodes {
				display: flex;
				flex-direction: row;
				gap: 2rem;
				padding: 1rem 0;
				align-items: flex-start;
				justify-content: flex-start;

				.timemachine,
				.heatmap {
					display: flex;
					flex-direction: column;
					align-items: center;
					justify-content: center;

					.button {
						flex: 0 0 5rem;
						width: 5rem;
						border-radius: 2 * $borderRadius;
						padding: 1rem;
					}
					h2 {
						margin: 1 0 0.5rem 0;
						text-align: center;
					}
				}
			}
		}

		.label {
			font-weight: 600;
			font-size: 1.2rem;
			display: flex;
			flex-direction: row;
			align-items: center;
			gap: 0.5rem;

			.label-text {
				display: flex;
				flex-direction: column;
				gap: 0.2rem;

				h1 {
					margin: 0;
					font-size: 1.2rem;
				}

				h2 {
					margin: 0;
					font-size: 1rem;
					font-weight: 400;
					color: var(--text-secondary);
					font-style: italic;
				}
			}

			svg {
				width: 1.5rem;
				height: 1.5rem;
				flex-shrink: 0;
			}
		}

		button.expand-small {
			margin-left: auto;
			width: 2.5rem;
			height: 2.5rem;
			background-color: transparent !important;
			color: var(--primary-glass-dark);
			&:hover {
				color: var(--primary-glass-shine);
			}
			.icon {
				transition: transform $transition;

				&.open {
					transform: scaleY(-1);
				}
			}
		}
	}
}
</style>
