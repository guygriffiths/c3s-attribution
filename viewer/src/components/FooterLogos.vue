<template>
	<div class="footer-logos">
		<a href="https://www.copernicus.eu/en" target="_blank" rel="noopener">
			<span class="sr-only">Copernicus European Union Programme</span>
			<img
				src="@/assets/img/eu-negative-logo.webp"
				alt="European Union Logo"
				class="logo"
				aria-hidden="true"
			/>
		</a>
		<a href="https://www.copernicus.eu/en" target="_blank" rel="noopener">
			<span class="sr-only">Copernicus European Union Programme</span>
			<img
				src="@/assets/img/copernicus-negative-logo.webp"
				alt="Copernicus Programme Logo"
				class="logo"
				aria-hidden="true"
			/>
		</a>
		<a href="https://climate.copernicus.eu/" target="_blank" rel="noopener">
			<span class="sr-only">
				Copernicus Climate Change Service (C3S) - European Climate Observations,
				Modelling and Services
			</span>
			<img
				src="@/assets/img/c3s-negative-logo.webp"
				alt="Copernicus Climate Change Service Logo"
				class="logo"
				aria-hidden="true"
			/>
		</a>
		<a href="https://www.ecmwf.int/" target="_blank" rel="noopener">
			<span class="sr-only">
				European Centre for Medium-Range Weather Forecasts (ECMWF)
			</span>
			<img
				src="@/assets/img/ecmwf-negative-logo.png"
				alt="ECMWF Logo"
				class="logo"
				aria-hidden="true"
			/>
		</a>
	</div>
</template>
<style lang="scss" scoped>
@use '@/assets/styles/scssVars.module.scss' as *;

.footer-logos {
	display: flex;
	align-items: center;
	justify-content: center;
	background: var(--panel-bg-night);
	backdrop-filter: $frosty;
	padding: 0.25rem 0.5rem;
	border-radius: $borderRadius;
	border-bottom-right-radius: 0;
	border-bottom-left-radius: 0;
	box-shadow: var(--shadow-md);
	gap: 1rem;

	.logo {
		height: 2rem;
		width: auto;
	}
}
</style>
