package org.grobid.core.test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;

import java.util.List;

import org.grobid.core.data.Affiliation;
import org.grobid.core.engines.Engine;
import org.grobid.core.factory.GrobidFactory;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.Test;

import static org.hamcrest.Matchers.hasSize;
import static org.junit.Assert.*;

public class TestAffiliationAddressParser extends EngineTest{
	
	@Before
	public void init(){
		engine = new Engine(false);
	}

    @AfterClass
    public static void tearDown(){
        GrobidFactory.reset();
    }
	
	@Test
	public void testParser() throws Exception {

		String affiliationSequence1 = "Atomic Physics Division, Department of Atomic Physics and Luminescence, " + 
									  "Faculty of Applied Physics and Mathematics, Gdansk University of " + 
									  "Technology, Narutowicza 11/12, 80-233 Gdansk, Poland";			
		List<Affiliation> res = engine.processAffiliation(affiliationSequence1);
        
        assertThat(res, hasSize(1));
        
        assertNotNull(res.get(0).getInstitutions());
        assertThat(res.get(0).getInstitutions(), hasSize(1));
        assertEquals(res.get(0).getInstitutions().get(0), "Gdansk University of Technology");
        assertEquals(res.get(0).getCountry(), "Poland");
        assertEquals(res.get(0).getAddrLine(), "Narutowicza 11/12");
        assertEquals(res.get(0).getPostCode(), "80-233");
        
        assertThat(res.get(0).getDepartments(), hasSize(2));
        assertEquals(res.get(0).getDepartments().get(0), "Department of Atomic Physics and Luminescence");
        assertEquals(res.get(0).getDepartments().get(1), "Faculty of Applied Physics and Mathematics");
        
        assertThat(res.get(0).getLaboratories(), hasSize(1));
        assertEquals(res.get(0).getLaboratories().get(0), "Atomic Physics Division");
	}

	@Test
    public void testParser2() throws Exception {
        String affiliationSequence2 = "Faculty of Health, School of Biomedical Sciences, " +
            "University of Newcastle, New South Wales, Australia.";
        List<Affiliation> res = engine.processAffiliation(affiliationSequence2);
        assertThat(res, hasSize(1));
        assertEquals(res.get(0).getInstitutions().get(0), "University of Newcastle");

        assertThat(res.get(0).getDepartments(), hasSize(2));
        assertEquals(res.get(0).getDepartments().get(0), "Faculty of Health");
        assertEquals(res.get(0).getDepartments().get(1), "School of Biomedical Sciences");
    }
}