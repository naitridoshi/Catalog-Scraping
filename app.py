import streamlit as st
import pandas as pd
import asyncio
import zipfile
import io
import os

# Import runner functions
from alShamali.main import run_alshamali_scraper_and_return_df
from dljParts.main import run_dljparts_scraper
from insta_cafe.main import run_insta_cafe_scraper_and_return_df
from Jinku.main import run_jinku_scraper
from MrMedia.main import run_mr_media_scraper_and_return_df
from qatar.main import run_qatar_scraper_and_return_df
from sbParts.main import run_sbparts_scraper_for_part_number
from supreme_motors.main import run_supreme_motors_scraper_and_return_df
from suzuki.main import run_suzuki_scraper_and_return_df
from worldTraders.main import run_world_traders_scraper_and_return_df

# Import UI render functions
from ui import alshamali, dlj_parts, insta_cafe, jinku, mr_media, qatar, sb_parts, supreme_motors, suzuki, world_traders

SCRAPER_CONFIG = {
    "DLJ Parts": {"ui": dlj_parts.render, "runner": run_dljparts_scraper, "async": False},
    "Jikiu": {"ui": jinku.render, "runner": run_jinku_scraper, "async": False, "validate": lambda x: x and len(str(x)) >= 4, "error_msg": "Please provide a product ID with at least 4 digits."},
    "SB Parts": {"ui": sb_parts.render, "runner": run_sbparts_scraper_for_part_number, "async": True, "validate": lambda x: x and len(str(x)) >= 4, "error_msg": "Please provide a product ID with at least 4 digits."},
    "Suzuki": {"ui": suzuki.render, "runner": run_suzuki_scraper_and_return_df, "async": True},
    "Mr. Media": {"ui": mr_media.render, "runner": run_mr_media_scraper_and_return_df, "async": False},
    "AlShamali": {"ui": alshamali.render, "runner": run_alshamali_scraper_and_return_df, "async": True},
    # "Qatar CID": {"ui": qatar.render, "runner": run_qatar_scraper_and_return_df, "async": False},
    # "Supreme Motors": {"ui": supreme_motors.render, "runner": run_supreme_motors_scraper_and_return_df, "async": True},
    # "World Traders": {"ui": world_traders.render, "runner": run_world_traders_scraper_and_return_df, "async": False},
}

def display_advanced_results(scraper_name, combined_df, results_list):
    st.success("Scraping complete!")

    # If we have a single combined dataframe
    if combined_df is not None and not combined_df.empty:
        st.dataframe(combined_df)
        csv = combined_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name=f'{scraper_name.replace(" ", "_").lower()}_combined_data.csv',
            mime='text/csv',
        )
    
    # If we have separate brand/category results
    elif results_list:
        summary_data = [{
            'Category': r['title'], 
            'Items Scraped': r['count'], 
            'Status': r['status']
        } for r in results_list]
        summary_df = pd.DataFrame(summary_data)
        
        st.write("### Scraping Summary")
        st.dataframe(summary_df)

        csv = summary_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download summary as CSV",
            data=csv,
            file_name=f'{scraper_name.replace(" ", "_").lower()}_summary.csv',
            mime='text/csv',
        )

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED, False) as zip_file:
            for r in results_list:
                if r['csv_content']:
                    file_name = f"{r['title'].strip().replace(' ', '_').replace('/', '_')}_data.csv"
                    zip_file.writestr(file_name, r['csv_content'])
        
        st.download_button(
            label="Download all files as ZIP",
            data=zip_buffer.getvalue(),
            file_name=f"{scraper_name.replace(" ", "_").lower()}_files.zip",
            mime="application/zip"
        )

        st.write("--- ")
        st.write("### Data Preview")
        for r in results_list:
            with st.expander(f"{r['title']} ({r['count']} items)"):
                st.dataframe(r['dataframe'])
    else:
        st.error("Scraping failed or returned no data.")

st.title("Auto Parts & Directory Scraper")
st.info("Note: This is a tool for running various web scrapers. Please use responsibly.")

selected_scraper = st.selectbox("Choose a scraper to run:", list(SCRAPER_CONFIG.keys()))

st.header(f"Options for {selected_scraper}")

config = SCRAPER_CONFIG[selected_scraper]
input_value = config["ui"]()

if st.button(f"Run {selected_scraper} Scraper"):
    is_valid = True
    if selected_scraper in ["AlShamali", "Mr. Media"]:
        if not input_value or not input_value[0]:
            st.warning("Please select at least one category.")
            is_valid = False
    elif not input_value:
        st.warning("Please provide an input.")
        is_valid = False
    elif "validate" in config and not config["validate"](input_value):
        st.warning(config["error_msg"])
        is_valid = False

    if is_valid:
        with st.spinner(f"Running the {selected_scraper} scraper... Please wait."):
            try:
                runner = config["runner"]
                
                # Custom handling for scrapers with advanced output options
                if selected_scraper in ["AlShamali", "Mr. Media", "Suzuki"]:
                    # The runner for these scrapers returns a tuple: (combined_df, results_list)
                    combined_df, results_list = asyncio.run(runner(*input_value)) if config["async"] else runner(*input_value)
                    display_advanced_results(selected_scraper, combined_df, results_list)

                # Standard handling for other scrapers
                else:
                    result_df = pd.DataFrame()
                    if config["async"]:
                        result_df = asyncio.run(runner(input_value))
                    else:
                        result_df = runner(input_value)

                    if not result_df.empty:
                        st.success("Scraping complete!")
                        st.dataframe(result_df)
                        csv = result_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download data as CSV",
                            data=csv,
                            file_name=f'{selected_scraper.replace(" ", "_").lower()}_data.csv',
                            mime='text/csv',
                        )
                    else:
                        st.error("Scraping failed or returned no data.")

            except Exception as e:
                st.error(f"An error occurred: {e}")
